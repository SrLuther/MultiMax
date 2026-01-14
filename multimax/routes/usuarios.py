import os
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Sequence, cast

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import (
    AppSetting,
    Ciclo,
    CleaningHistory,
    CleaningTask,
    Collaborator,
    Historico,
    Holiday,
    JobRole,
    MedicalCertificate,
    NotificationRead,
    Produto,
    Shift,
    SystemLog,
    TimeOffRecord,
    User,
    Vacation,
)
from ..password_hash import check_password_hash, generate_password_hash

bp = Blueprint("usuarios", __name__)


def _is_dev(user):
    """Verifica se o usuário é desenvolvedor (acesso total)"""
    return user.nivel == "DEV"


def _can_manage_admins(user):
    """Verifica se o usuário pode gerenciar administradores (apenas DEV)"""
    return user.nivel == "DEV"


def _block_viewer_modifications():
    """Bloqueia visualizadores de fazer qualquer alteração (exceto perfil)"""
    if current_user.nivel == "visualizador":
        flash("Visualizadores não têm permissão para fazer alterações no sistema.", "danger")
        return True
    return False


@bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado. Apenas Gerente pode gerenciar usuários.", "danger")
        return redirect(url_for("estoque.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username_input = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        nivel = request.form.get("nivel", "visualizador").strip()
        # Apenas DEV pode criar ou alterar usuários para admin/DEV
        if nivel in ("admin", "DEV") and current_user.nivel != "DEV":
            flash("Apenas o desenvolvedor pode criar ou alterar administradores.", "danger")
            return redirect(url_for("usuarios.gestao"))
        if not name or not password:
            flash("Nome e senha são obrigatórios.", "warning")
            return redirect(url_for("usuarios.gestao"))
        if username_input:
            base_username = "".join(ch for ch in username_input.lower() if ch.isalnum()) or "user"
            username = base_username
            if User.query.filter_by(username=username).first() is not None:
                flash("Login já existe. Escolha outro.", "danger")
                return redirect(url_for("usuarios.gestao"))
        else:
            base_username = "".join(ch for ch in name.lower() if ch.isalnum()) or "user"
            username = base_username
            suffix = 1
            while User.query.filter_by(username=username).first() is not None:
                username = f"{base_username}{suffix}"
                suffix += 1
        new_user = User()
        new_user.name = name
        new_user.username = username
        new_user.nivel = nivel
        new_user.password_hash = generate_password_hash(password)
        try:
            db.session.add(new_user)
            log = SystemLog()
            log.origem = "Usuarios"
            log.evento = "criar"
            log.detalhes = f"Criado {name} ({username}) nivel {nivel}"
            log.usuario = current_user.name
            db.session.add(log)
            db.session.commit()
            flash(f'Usuário "{name}" criado com login "{username}".', "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar usuário: {e}", "danger")
        return redirect(url_for("usuarios.gestao"))
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/vps/restart", methods=["POST"])
@login_required
def gestao_vps_restart():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Administradores podem reiniciar a VPS.", "danger")
        return redirect(url_for("usuarios.gestao"))
    secret_in = (request.form.get("secret_key") or "").strip()
    secret_cfg = str(current_app.config.get("SECRET_KEY") or "").strip()
    if not secret_in or secret_in != secret_cfg:
        flash("Senha inválida para reiniciar a VPS.", "danger")
        return redirect(url_for("usuarios.gestao"))
    try:
        cmd = (os.getenv("VPS_REBOOT_CMD") or "sudo reboot").strip()
        subprocess.Popen(cmd, shell=True)
        flash("Reinício da VPS iniciado.", "warning")
    except Exception as e:
        flash(f"Falha ao reiniciar VPS: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/vps/upload", methods=["POST"])
@login_required
def gestao_vps_upload():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Administradores podem atualizar a VPS.", "danger")
        return redirect(url_for("usuarios.gestao"))
    secret_in = (request.form.get("secret_key") or "").strip()
    secret_cfg = str(current_app.config.get("SECRET_KEY") or "").strip()
    if not secret_in or secret_in != secret_cfg:
        flash("Senha inválida para atualizar a VPS.", "danger")
        return redirect(url_for("usuarios.gestao"))
    file = request.files.get("zipfile")
    if not file or not (file.filename or "").lower().endswith(".zip"):
        flash("Selecione um arquivo .zip válido.", "warning")
        return redirect(url_for("usuarios.gestao"))
    tmp_dir = tempfile.mkdtemp(prefix="mmx_up_")
    zip_path = os.path.join(tmp_dir, "update.zip")
    try:
        file.save(zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)
        root = Path(current_app.root_path).resolve()
        extracted_root = Path(tmp_dir).resolve()
        copied = 0
        for p in extracted_root.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(extracted_root)
            target = (root / rel).resolve()
            try:
                if str(target).startswith(str(root)):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(p), str(target))
                    copied += 1
            except Exception:
                pass
        setup_script = root / "vps_setup.sh"
        alt_setup_script = root / "scripts" / "vps_setup.sh"
        run_script = setup_script if setup_script.exists() else alt_setup_script
        if run_script.exists():
            try:
                subprocess.Popen(["bash", str(run_script)], cwd=str(root))
            except Exception:
                pass
        try:
            cmd = (os.getenv("VPS_REBOOT_CMD") or "sudo reboot").strip()
            subprocess.Popen(cmd, shell=True)
        except Exception:
            pass
        flash(f"Atualização aplicada ({copied} arquivos). VPS será reiniciada.", "success")
    except Exception as e:
        flash(f"Falha ao aplicar atualização: {e}", "danger")
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/restart", methods=["POST"])
@login_required
def gestao_restart():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Administradores podem reiniciar.", "danger")
        return redirect(url_for("usuarios.gestao"))
    secret_in = (request.form.get("secret_key") or "").strip()
    secret_cfg = str(current_app.config.get("SECRET_KEY") or "").strip()
    if not secret_in or secret_in != secret_cfg:
        flash("Senha inválida para reinício do sistema.", "danger")
        return redirect(url_for("usuarios.gestao"))
    try:
        cmd = (os.getenv("RESTART_CMD") or "").strip()
        if cmd:
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception:
                pass

        def _do_exit():
            time.sleep(1.0)
            try:
                os._exit(0)
            except Exception:
                pass

        threading.Thread(target=_do_exit, daemon=True).start()
        flash("Reiniciando MultiMax na VPS...", "warning")
    except Exception as e:
        flash(f"Falha ao iniciar reinício: {e}", "danger")
    return redirect(url_for("home.index"))


@bp.route("/users/<int:user_id>/senha", methods=["POST"])
@login_required
def update_password(user_id):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para atualizar senhas.", "danger")
        return redirect(url_for("estoque.index"))
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "").strip()
    if not new_password:
        flash("Informe a nova senha.", "warning")
        return redirect(url_for("usuarios.users"))
    try:
        user.password_hash = generate_password_hash(new_password)
        log = SystemLog()
        log.origem = "Usuarios"
        log.evento = "senha"
        log.detalhes = f"Senha atualizada para {user.username}"
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" atualizada.', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar senha: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/users/<int:user_id>/reset_senha", methods=["POST"])
@login_required
def reset_password(user_id):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para redefinir senhas.", "danger")
        return redirect(url_for("estoque.index"))
    user = User.query.get_or_404(user_id)
    default_password = "123456"
    try:
        user.password_hash = generate_password_hash(default_password)
        log = SystemLog()
        log.origem = "Usuarios"
        log.evento = "senha"
        log.detalhes = f"Senha redefinida para {user.username}"
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" redefinida.', "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao redefinir senha: {e}", "danger")
    return redirect(url_for("usuarios.users"))


@bp.route("/users/<int:user_id>/nivel", methods=["POST"])
@login_required
def update_level(user_id):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para alterar níveis de usuário.", "danger")
        return redirect(url_for("estoque.index"))
    user = User.query.get_or_404(user_id)
    nivel = request.form.get("nivel", "visualizador").strip()
    if nivel not in ("visualizador", "operador", "admin", "DEV"):
        flash("Nível inválido.", "warning")
        return redirect(url_for("usuarios.gestao"))
    # Apenas DEV pode alterar nível para admin/DEV
    if nivel in ("admin", "DEV") and current_user.nivel != "DEV":
        flash("Apenas o desenvolvedor pode alterar usuários para administrador.", "danger")
        return redirect(url_for("usuarios.gestao"))
    try:
        user.nivel = nivel
        log = SystemLog()
        log.origem = "Usuarios"
        log.evento = "nivel"
        log.detalhes = f"Nivel {user.username} -> {nivel}"
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Nivel do usuário "{user.name}" atualizado para "{nivel}".', "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar nível: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/users/<int:user_id>/excluir", methods=["POST"])
@login_required
def excluir_user(user_id):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para excluir usuários.", "danger")
        return redirect(url_for("estoque.index"))
    if current_user.id == user_id:
        flash("Você não pode excluir sua própria conta.", "warning")
        return redirect(url_for("usuarios.users"))
    user = User.query.get_or_404(user_id)
    # Apenas DEV pode excluir administradores
    if user.nivel in ("admin", "DEV") and current_user.nivel != "DEV":
        flash("Apenas o desenvolvedor pode excluir administradores.", "danger")
        return redirect(url_for("usuarios.users"))
    try:
        db.session.delete(user)
        log = SystemLog()
        log.origem = "Usuarios"
        log.evento = "excluir"
        log.detalhes = f"Excluido {user.name} ({user.username})"
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Usuário "{user.name}" excluído com sucesso.', "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir usuário: {e}", "danger")
    return redirect(url_for("usuarios.users"))


@bp.route("/monitor")
@login_required
def monitor():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado. Apenas Administradores.", "danger")
        return redirect(url_for("estoque.index"))
    return redirect(url_for("usuarios.gestao"))


@bp.route("/notifications/read")
@login_required
def notifications_read():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Administradores podem resolver notificações.", "danger")
        return redirect(url_for("home.index"))
    tipo = request.args.get("tipo")
    ref_id = request.args.get("id", type=int)
    nxt = request.args.get("next", url_for("estoque.index"))
    if tipo in ("estoque", "limpeza") and ref_id:
        try:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo=tipo, ref_id=ref_id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = tipo
                nr.ref_id = ref_id
                db.session.add(nr)
                db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(nxt)


@bp.route("/notifications/unread")
@login_required
def notifications_unread():
    tipo = request.args.get("tipo")
    ref_id = request.args.get("id", type=int)
    nxt = request.args.get("next", url_for("estoque.index"))
    if tipo in ("estoque", "limpeza") and ref_id:
        try:
            NotificationRead.query.filter_by(user_id=current_user.id, tipo=tipo, ref_id=ref_id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(nxt)


@bp.route("/notifications/unread_all")
@login_required
def notifications_unread_all():
    nxt = request.args.get("next", url_for("estoque.index"))
    try:
        NotificationRead.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(nxt)


@bp.route("/notifications/read_all")
@login_required
def notifications_read_all():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Administradores podem resolver notificações.", "danger")
        return redirect(url_for("home.index"))
    nxt = request.args.get("next", url_for("home.index"))
    try:
        crit = (
            Produto.query.filter(
                Produto.estoque_minimo.isnot(None),
                Produto.estoque_minimo > 0,
                Produto.quantidade <= Produto.estoque_minimo,
            )
            .order_by(Produto.nome.asc())
            .limit(100)
            .all()
        )
        for p in crit:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo="estoque", ref_id=p.id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = "estoque"
                nr.ref_id = p.id
                db.session.add(nr)
        from datetime import date as _date
        from datetime import timedelta as _td

        horizon = _date.today() + _td(days=3)
        tasks = (
            CleaningTask.query.filter(CleaningTask.proxima_data.isnot(None), CleaningTask.proxima_data <= horizon)
            .order_by(CleaningTask.proxima_data.asc())
            .limit(100)
            .all()
        )
        for t in tasks:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo="limpeza", ref_id=t.id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = "limpeza"
                nr.ref_id = t.id
                db.session.add(nr)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    return redirect(nxt)


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        # Visualizadores podem alterar apenas nome e senha (não username)
        if current_user.nivel == "visualizador":
            name = (request.form.get("name") or "").strip()
            if not name:
                flash("Nome é obrigatório.", "warning")
                return redirect(url_for("usuarios.perfil"))
            current_user.name = name
        else:
            # Outros níveis podem alterar nome e username
            name = (request.form.get("name") or "").strip()
            username_input = (request.form.get("username") or "").strip().lower()
            if not name:
                flash("Nome é obrigatório.", "warning")
                return redirect(url_for("usuarios.perfil"))
            if not username_input:
                flash("Login é obrigatório.", "warning")
                return redirect(url_for("usuarios.perfil"))
            base_username = "".join(ch for ch in username_input if ch.isalnum())
            if not base_username:
                flash("Login deve conter apenas letras e números.", "warning")
                return redirect(url_for("usuarios.perfil"))
            if base_username != current_user.username:
                if User.query.filter_by(username=base_username).first() is not None:
                    flash("Login já existe. Escolha outro.", "danger")
                    return redirect(url_for("usuarios.perfil"))
                current_user.username = base_username
            current_user.name = name
        try:
            db.session.commit()
            flash("Perfil atualizado.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar perfil: {e}", "danger")
        return redirect(url_for("usuarios.perfil"))
    try:
        from sqlalchemy import inspect, text

        insp = inspect(db.engine)
        cols_meta = [c["name"] for c in insp.get_columns("collaborator")]
        if "user_id" not in cols_meta:
            db.session.execute(text("ALTER TABLE collaborator ADD COLUMN user_id INTEGER"))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    # User e Collaborator são uma coisa só - buscar colaborador vinculado ao usuário
    collab = None
    balance_data = None
    entries = []

    try:
        collab = Collaborator.query.filter_by(user_id=current_user.id).first()
        if collab:
            # Usar função do sistema de Ciclos
            from ..routes.ciclos import _calculate_collaborator_balance

            # Calcular saldo usando o sistema de Ciclos
            balance = _calculate_collaborator_balance(collab.id)

            balance_data = {
                "total_horas": balance["total_horas"],
                "dias_completos": balance["dias_completos"],
                "horas_restantes": balance["horas_restantes"],
                "valor_aproximado": balance["valor_aproximado"],
            }

            # Buscar registros ativos para exibição
            entries = (
                Ciclo.query.filter(Ciclo.collaborator_id == collab.id, Ciclo.status_ciclo == "ativo")
                .order_by(Ciclo.data_lancamento.desc(), Ciclo.id.desc())
                .limit(50)
                .all()
            )
    except Exception:
        collab = None
        balance_data = None

    # Variáveis de saldo para compatibilidade
    residual_hours = balance_data["horas_restantes"] if balance_data else 0.0
    dias_completos = balance_data["dias_completos"] if balance_data else 0

    # Calcular valores monetários a receber
    collaborator_values = None
    day_value = 0.0
    if collab and balance_data:
        try:
            # Obter valor por dia (sistema de Ciclos)
            try:
                setting = AppSetting.query.filter_by(key="ciclo_valor_dia").first()
                if setting and setting.value:
                    day_value = float(setting.value)
                else:
                    day_value = 65.0  # Valor padrão
            except Exception:
                day_value = 65.0  # Valor padrão

            # Usar valores já calculados pelo sistema de Ciclos
            collaborator_values = {
                "full_days": balance_data["dias_completos"],
                "residual_hours": balance_data["horas_restantes"],
                "day_value": day_value,
                "value_full_days": balance_data["valor_aproximado"],
                "value_residual_hours": 0.0,  # Horas restantes não entram na conversão
                "value_total_individual": balance_data["valor_aproximado"],
            }
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular valores do colaborador: {e}")
            collaborator_values = None
            day_value = 0.0

    is_on_break = False
    is_on_vacation = False
    vacation_end_date = None
    vacation_end_timestamp = 0
    vacation_return_hour = "05:00"
    is_on_medical = False
    medical_end_timestamp = 0
    medical_end_date = None
    break_end_timestamp = 0
    next_shift_date = None
    next_shift_hour = None

    if collab:
        from datetime import date as _date
        from datetime import datetime as _dt
        from datetime import timedelta as _td

        today = _date.today()

        try:
            today_shift = Shift.query.filter_by(collaborator_id=collab.id, date=today).first()
            if today_shift and (
                (today_shift.shift_type or "").lower() == "folga" or (today_shift.turno or "").lower() == "folga"
            ):
                is_on_break = True
                end_dt = _dt.combine(today, _dt.min.time().replace(hour=23, minute=59, second=59))
                break_end_timestamp = int(end_dt.timestamp())
        except Exception:
            pass
        try:
            ns = (
                Shift.query.filter(Shift.collaborator_id == collab.id, Shift.date >= today, Shift.shift_type != "folga")
                .order_by(Shift.date.asc())
                .first()
            )
            if ns:
                next_shift_date = ns.date
                if ns.start_dt:
                    next_shift_hour = ns.start_dt.strftime("%H:%M")
                else:
                    st = (ns.shift_type or "").lower()
                    if st.startswith("abertura"):
                        next_shift_hour = "05:00"
                    elif st == "tarde":
                        next_shift_hour = "09:30"
                    elif st.startswith("domingo"):
                        next_shift_hour = "05:00"
                    else:
                        next_shift_hour = "05:00"
        except Exception:
            pass
        # Folgas utilizadas agora são registradas no sistema de Ciclos com origem 'Folga utilizada'
        # Não precisamos mais verificar TimeOffRecord para folgas

        try:
            vacation = Vacation.query.filter(
                Vacation.collaborator_id == collab.id, Vacation.data_inicio <= today, Vacation.data_fim >= today
            ).first()
            if vacation:
                is_on_vacation = True
                vacation_end_date = vacation.data_fim.strftime("%d/%m/%Y")

                return_date = vacation.data_fim + _td(days=1)

                try:
                    next_shift = (
                        Shift.query.filter(
                            Shift.collaborator_id == collab.id, Shift.date >= return_date, Shift.shift_type != "folga"
                        )
                        .order_by(Shift.date.asc())
                        .first()
                    )

                    if next_shift:
                        return_date = next_shift.date
                        if next_shift.start_dt:
                            try:
                                vacation_return_hour = next_shift.start_dt.strftime("%H:%M")
                            except Exception:
                                vacation_return_hour = "05:00"
                        else:
                            st = (next_shift.shift_type or "").lower()
                            if st.startswith("abertura"):
                                vacation_return_hour = "05:00"
                            elif st == "tarde":
                                vacation_return_hour = "09:30"
                            elif st.startswith("domingo"):
                                vacation_return_hour = "05:00"
                            else:
                                vacation_return_hour = "05:00"
                except Exception:
                    pass

                try:
                    hour_parts = vacation_return_hour.split(":")
                    return_hour = int(hour_parts[0]) if hour_parts else 5
                    return_min = int(hour_parts[1]) if len(hour_parts) > 1 else 0
                except Exception:
                    return_hour, return_min = 5, 0

                return_datetime = _dt.combine(return_date, _dt.min.time().replace(hour=return_hour, minute=return_min))
                vacation_end_timestamp = int(return_datetime.timestamp())
        except Exception:
            pass

        try:
            mc = (
                MedicalCertificate.query.filter(
                    MedicalCertificate.collaborator_id == collab.id,
                    MedicalCertificate.data_inicio <= today,
                    MedicalCertificate.data_fim >= today,
                )
                .order_by(MedicalCertificate.data_fim.desc())
                .first()
            )
            if mc:
                is_on_medical = True
                medical_end_date = mc.data_fim.strftime("%d/%m/%Y")
                med_end_dt = _dt.combine(mc.data_fim, _dt.min.time().replace(hour=23, minute=59, second=59))
                medical_end_timestamp = int(med_end_dt.timestamp())
        except Exception:
            pass

    return render_template(
        "perfil.html",
        active_page="perfil",
        collab=collab,
        balance_data=balance_data,
        entries=entries,
        residual_hours=residual_hours,
        dias_completos=dias_completos,
        is_on_break=is_on_break,
        is_on_vacation=is_on_vacation,
        vacation_end_date=vacation_end_date,
        vacation_end_timestamp=vacation_end_timestamp,
        vacation_return_hour=vacation_return_hour,
        is_on_medical=is_on_medical,
        medical_end_timestamp=medical_end_timestamp,
        medical_end_date=medical_end_date,
        break_end_timestamp=break_end_timestamp,
        next_shift_date=next_shift_date,
        next_shift_hour=next_shift_hour,
        collaborator_values=collaborator_values,
        day_value=day_value,
    )


@bp.route("/perfil/senha", methods=["POST"])
@login_required
def perfil_senha():
    senha_atual = request.form.get("senha_atual", "")
    nova_senha = request.form.get("nova_senha", "")
    confirmar = request.form.get("confirmar_senha", "")
    if not nova_senha or len(nova_senha) < 6:
        flash("Nova senha deve ter ao menos 6 caracteres.", "warning")
        return redirect(url_for("usuarios.perfil"))
    if nova_senha != confirmar:
        flash("Confirmação de senha não confere.", "warning")
        return redirect(url_for("usuarios.perfil"))
    if not check_password_hash(current_user.password_hash or "", senha_atual):
        flash("Senha atual inválida.", "danger")
        return redirect(url_for("usuarios.perfil"))
    try:
        current_user.password_hash = generate_password_hash(nova_senha)
        db.session.commit()
        flash("Senha atualizada com sucesso.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar senha: {e}", "danger")
    return redirect(url_for("usuarios.perfil"))


@bp.route("/gestao", methods=["GET"])
@login_required
def gestao():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado. Apenas Administradores.", "danger")
        return redirect(url_for("estoque.index"))
    q = (request.args.get("q") or "").strip()
    view = (request.args.get("view") or "").strip()
    # QR removido
    try:
        from sqlalchemy import inspect, text

        insp = inspect(db.engine)
        cols_meta = [c["name"] for c in insp.get_columns("collaborator")]
        changed = False
        if "name" not in cols_meta:
            db.session.execute(text("ALTER TABLE collaborator ADD COLUMN name TEXT"))
            changed = True
            if "nome" in cols_meta:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = nome WHERE name IS NULL"))
                except Exception:
                    pass
            else:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = '' WHERE name IS NULL"))
                except Exception:
                    pass
        if changed:
            db.session.commit()
        # Garantir colunas necessárias em tabelas de gestão
        # Verificar se as tabelas existem antes de inspecioná-las
        try:
            tables = insp.get_table_names()

            # leave_assignment: notes (tabela antiga, pode não existir)
            if "leave_assignment" in tables:
                try:
                    la_cols = [c["name"] for c in insp.get_columns("leave_assignment")]
                    la_changed = False
                    if "notes" not in la_cols:
                        db.session.execute(text("ALTER TABLE leave_assignment ADD COLUMN notes TEXT"))
                        la_changed = True
                    if la_changed:
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            # leave_credit: origin, notes (tabela antiga, pode não existir)
            if "leave_credit" in tables:
                try:
                    lc_cols = [c["name"] for c in insp.get_columns("leave_credit")]
                    lc_changed = False
                    if "origin" not in lc_cols:
                        db.session.execute(text("ALTER TABLE leave_credit ADD COLUMN origin TEXT"))
                        lc_changed = True
                    if "notes" not in lc_cols:
                        db.session.execute(text("ALTER TABLE leave_credit ADD COLUMN notes TEXT"))
                        lc_changed = True
                    if lc_changed:
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            # hour_bank_entry: reason (tabela antiga, pode não existir)
            if "hour_bank_entry" in tables:
                try:
                    hb_cols = [c["name"] for c in insp.get_columns("hour_bank_entry")]
                    hb_changed = False
                    if "reason" not in hb_cols:
                        db.session.execute(text("ALTER TABLE hour_bank_entry ADD COLUMN reason TEXT"))
                        hb_changed = True
                    if hb_changed:
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            # vacation: observacao
            if "vacation" in tables:
                try:
                    vac_cols = [c["name"] for c in insp.get_columns("vacation")]
                    vac_changed = False
                    if "observacao" not in vac_cols:
                        db.session.execute(text("ALTER TABLE vacation ADD COLUMN observacao TEXT"))
                        vac_changed = True
                    if vac_changed:
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            # medical_certificate: motivo, cid, medico, foto_atestado
            if "medical_certificate" in tables:
                try:
                    mc_cols = [c["name"] for c in insp.get_columns("medical_certificate")]
                    mc_changed = False
                    if "motivo" not in mc_cols:
                        db.session.execute(text("ALTER TABLE medical_certificate ADD COLUMN motivo TEXT"))
                        mc_changed = True
                    if "cid" not in mc_cols:
                        db.session.execute(text("ALTER TABLE medical_certificate ADD COLUMN cid TEXT"))
                        mc_changed = True
                    if "medico" not in mc_cols:
                        db.session.execute(text("ALTER TABLE medical_certificate ADD COLUMN medico TEXT"))
                        mc_changed = True
                    if "foto_atestado" not in mc_cols:
                        db.session.execute(text("ALTER TABLE medical_certificate ADD COLUMN foto_atestado TEXT"))
                        mc_changed = True
                    if mc_changed:
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        u_page = int(request.args.get("u_page", "1"))
    except Exception:
        u_page = 1
    try:
        l_page = int(request.args.get("l_page", "1"))
    except Exception:
        l_page = 1
    if u_page < 1:
        u_page = 1
    if l_page < 1:
        l_page = 1
    hist_estoque = Historico.query.order_by(Historico.data.desc()).limit(50).all()
    hist_limpeza = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(50).all()
    hist_sistema = SystemLog.query.order_by(SystemLog.data.desc()).limit(50).all()
    logs = []
    for h in hist_estoque:
        logs.append(
            {
                "data": h.data,
                "origem": "Estoque",
                "evento": h.action,
                "detalhes": h.details,
                "usuario": h.usuario,
                "produto": h.product_name,
                "quantidade": h.quantidade,
            }
        )
    for h in hist_limpeza:
        logs.append(
            {
                "data": h.data_conclusao,
                "origem": "Limpeza",
                "evento": "conclusao",
                "detalhes": h.observacao,
                "usuario": h.usuario_conclusao,
                "produto": h.nome_limpeza,
                "quantidade": None,
            }
        )
    for s in hist_sistema:
        logs.append(
            {
                "data": s.data,
                "origem": s.origem,
                "evento": s.evento,
                "detalhes": s.detalhes,
                "usuario": s.usuario,
                "produto": None,
                "quantidade": None,
            }
        )
    logs.sort(key=lambda x: x["data"], reverse=True)
    # Colaboradores (User e Collaborator são uma coisa só)
    try:
        colaboradores = Collaborator.query.order_by(Collaborator.name.asc()).all()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Erro ao buscar colaboradores: {e}", exc_info=True)
        colaboradores = []

    # Função auxiliar para obter nome de exibição
    def _get_display_name(collab):
        try:
            if collab.user_id and collab.user:
                return collab.user.name or ""
            return collab.name or ""
        except Exception:
            return ""

    # Adicionar display_name a cada colaborador
    for c in colaboradores:
        try:
            c.display_name = _get_display_name(c)
        except Exception:
            c.display_name = ""

    # Busca e paginação - mostrar colaboradores (User e Collaborator são uma coisa só)
    # Filtrar colaboradores por nome (busca no nome do User se existir, senão no do Collaborator)
    colaboradores_filtrados = colaboradores
    if q:
        # Buscar colaboradores cujo nome ou nome do usuário corresponda
        try:
            colaboradores_filtrados = []
            for c in colaboradores:
                try:
                    nome_busca = ""
                    if c.user and c.user.name:
                        nome_busca = c.user.name.lower()
                    elif c.name:
                        nome_busca = c.name.lower()
                    if q.lower() in nome_busca:
                        colaboradores_filtrados.append(c)
                except Exception:
                    continue
        except Exception:
            colaboradores_filtrados = colaboradores

    # Paginação de colaboradores (substituindo users_page)
    per_users = 5
    total_users = len(colaboradores_filtrados)
    u_total_pages = max(1, (total_users + per_users - 1) // per_users)
    if u_page > u_total_pages:
        u_page = u_total_pages
    u_start = (u_page - 1) * per_users
    u_end = u_start + per_users
    users_page = colaboradores_filtrados[u_start:u_end]  # Agora mostra colaboradores, não users separados

    # Manter all_users para compatibilidade com modais
    all_users = User.query.all()

    # Paginação de logs
    per_logs = 2
    total_logs = len(logs)
    l_total_pages = max(1, (total_logs + per_logs - 1) // per_logs)
    if l_page > l_total_pages:
        l_page = l_total_pages
    l_start = (l_page - 1) * per_logs
    l_end = l_start + per_logs
    logs_page = logs[l_start:l_end]

    # Registro de Acessos (pagina e filtra por usuário)
    try:
        acc_user = (request.args.get("acc_user") or "").strip()
    except Exception:
        acc_user = ""
    try:
        acc_page = int(request.args.get("acc_page", "1"))
    except Exception:
        acc_page = 1
    if acc_page < 1:
        acc_page = 1
    aq = SystemLog.query.filter(SystemLog.origem == "Acesso", SystemLog.evento == "login")
    if acc_user:
        aq = aq.filter(SystemLog.usuario.ilike(f"%{acc_user}%"))
    access_all = aq.order_by(SystemLog.data.desc()).all()
    per_acc = 10
    acc_total = len(access_all)
    acc_total_pages = max(1, (acc_total + per_acc - 1) // per_acc)
    if acc_page > acc_total_pages:
        acc_page = acc_total_pages
    acc_start = (acc_page - 1) * per_acc
    acc_end = acc_start + per_acc
    access_page = access_all[acc_start:acc_end]

    senha_sugestao = "123456"
    roles = JobRole.query.order_by(JobRole.name.asc()).all()
    bank_balances = {}
    saldo_collab = None
    saldo_hours = None
    saldo_days = None
    saldo_items = []
    saldo_start = None
    saldo_end = None
    try:
        from sqlalchemy import func

        sums = (
            db.session.query(TimeOffRecord.collaborator_id, func.coalesce(func.sum(TimeOffRecord.hours), 0.0))
            .filter(TimeOffRecord.record_type == "horas")
            .group_by(TimeOffRecord.collaborator_id)
            .all()
        )
        for cid, total in sums:
            bank_balances[int(cid)] = float(total or 0.0)
        try:
            scid = request.args.get("saldo_collaborator_id", type=int)
        except Exception:
            scid = None
        try:
            raw_start = request.args.get("saldo_start", "") or ""
            raw_end = request.args.get("saldo_end", "") or ""
            from datetime import datetime as _dt2

            if isinstance(raw_start, str) and raw_start.strip():
                saldo_start = _dt2.strptime(raw_start.strip(), "%Y-%m-%d").date()
            else:
                saldo_start = None
            if isinstance(raw_end, str) and raw_end.strip():
                saldo_end = _dt2.strptime(raw_end.strip(), "%Y-%m-%d").date()
            else:
                saldo_end = None
        except Exception:
            saldo_start = None
            saldo_end = None
        if scid:
            saldo_collab = Collaborator.query.get(scid)
            if saldo_collab:
                try:
                    hsum_pre = (
                        db.session.query(func.coalesce(func.sum(TimeOffRecord.hours), 0.0))
                        .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "horas")
                        .scalar()
                        or 0.0
                    )
                    hsum_pre = float(hsum_pre)
                    auto_pre = (
                        db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                        .filter(
                            TimeOffRecord.collaborator_id == scid,
                            TimeOffRecord.record_type == "folga_adicional",
                            TimeOffRecord.origin == "horas",
                        )
                        .scalar()
                        or 0
                    )
                    auto_pre = int(auto_pre)
                    desired_pre = int(hsum_pre // 8.0) if hsum_pre > 0.0 else 0
                    missing_pre = max(0, desired_pre - auto_pre)
                    if missing_pre > 0:
                        from datetime import date as _date

                        for _ in range(missing_pre):
                            lc = TimeOffRecord()
                            lc.collaborator_id = scid
                            lc.date = _date.today()
                            lc.record_type = "folga_adicional"
                            lc.days = 1
                            lc.origin = "horas"
                            lc.notes = "Reconciliação automática: crédito por 8h acumuladas"
                            lc.created_by = "sistema"
                            db.session.add(lc)
                        for _ in range(missing_pre):
                            adj = TimeOffRecord()
                            adj.collaborator_id = scid
                            adj.date = _date.today()
                            adj.record_type = "horas"
                            adj.hours = -8.0
                            adj.notes = "Reconciliação automática: -8h por +1 dia"
                            adj.origin = "sistema"
                            adj.created_by = "sistema"
                            db.session.add(adj)
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                # Calcular total bruto de horas (somando apenas horas positivas, sem considerar conversões negativas)
                total_bruto_hours = float(
                    db.session.query(
                        func.coalesce(func.sum(func.case((TimeOffRecord.hours > 0, TimeOffRecord.hours), else_=0)), 0.0)
                    )
                    .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "horas")
                    .scalar()
                    or 0.0
                )
                # Calcular dias convertidos das horas brutas (8h = 1 dia)
                days_from_hours = int(total_bruto_hours // 8.0) if total_bruto_hours >= 0.0 else 0
                # Horas restantes após conversão
                if total_bruto_hours >= 0.0:
                    saldo_hours = total_bruto_hours % 8.0
                else:
                    saldo_hours = 0.0
                credits_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "folga_adicional")
                    .scalar()
                    or 0
                )
                assigned_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "folga_usada")
                    .scalar()
                    or 0
                )
                converted_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "conversao")
                    .scalar()
                    or 0
                )
                # Saldo de dias = folgas adicionais + dias convertidos das horas brutas - folgas usadas - conversões em dinheiro
                saldo_days = int(credits_sum) + days_from_hours - int(assigned_sum) - int(converted_sum)
                try:
                    # Detalhamento por período
                    hq = TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "horas"
                    )
                    cq = TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "folga_adicional"
                    )
                    aq = TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "folga_usada"
                    )
                    if saldo_start and saldo_end:
                        hq = hq.filter(TimeOffRecord.date.between(saldo_start, saldo_end))
                        cq = cq.filter(TimeOffRecord.date.between(saldo_start, saldo_end))
                        aq = aq.filter(TimeOffRecord.date.between(saldo_start, saldo_end))
                    elif saldo_start:
                        hq = hq.filter(TimeOffRecord.date >= saldo_start)
                        cq = cq.filter(TimeOffRecord.date >= saldo_start)
                        aq = aq.filter(TimeOffRecord.date >= saldo_start)
                    elif saldo_end:
                        hq = hq.filter(TimeOffRecord.date <= saldo_end)
                        cq = cq.filter(TimeOffRecord.date <= saldo_end)
                        aq = aq.filter(TimeOffRecord.date <= saldo_end)
                    h_list = hq.order_by(TimeOffRecord.date.desc()).all()
                    c_list = cq.order_by(TimeOffRecord.date.desc()).all()
                    a_list = aq.order_by(TimeOffRecord.date.desc()).all()
                    # Unificar itens
                    for e in h_list:
                        saldo_items.append(
                            {
                                "tipo": "horas",
                                "date": e.date,
                                "amount": float(e.hours or 0.0),
                                "unit": "h",
                                "motivo": e.notes or "",
                            }
                        )
                    for c in c_list:
                        saldo_items.append(
                            {
                                "tipo": "credito",
                                "date": c.date,
                                "amount": int(c.days or 0),
                                "unit": "dia",
                                "motivo": (c.origin or "manual") + ((" — " + (c.notes or "")) if c.notes else ""),
                            }
                        )
                    for a in a_list:
                        saldo_items.append(
                            {
                                "tipo": "uso",
                                "date": a.date,
                                "amount": -int(a.days or 0),
                                "unit": "dia",
                                "motivo": a.notes or "",
                            }
                        )
                    saldo_items.sort(key=lambda x: x["date"], reverse=True)
                except Exception:
                    saldo_items = []
    except Exception:
        bank_balances = {}
    recent_entries = []
    try:
        recent_entries = (
            TimeOffRecord.query.filter(TimeOffRecord.record_type == "horas")
            .order_by(TimeOffRecord.date.desc())
            .limit(50)
            .all()
        )
    except Exception:
        recent_entries = []
    folgas = []
    try:
        from sqlalchemy import func

        for c in colaboradores:
            try:
                credits_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == c.id, TimeOffRecord.record_type == "folga_adicional")
                    .scalar()
                    or 0
                )
                assigned_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == c.id, TimeOffRecord.record_type == "folga_usada")
                    .scalar()
                    or 0
                )
                converted_sum = (
                    db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                    .filter(TimeOffRecord.collaborator_id == c.id, TimeOffRecord.record_type == "conversao")
                    .scalar()
                    or 0
                )
                folgas.append({"collab": c, "balance": int(credits_sum) - int(assigned_sum) - int(converted_sum)})
            except Exception:
                continue
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Erro ao calcular folgas: {e}", exc_info=True)
        folgas = []
    # Paginação e filtros por colaborador
    per_page = 10
    # Banco de Horas (lista de colaboradores)
    try:
        bh_collab_id = request.args.get("bh_collaborator_id", type=int)
    except Exception:
        bh_collab_id = None
    try:
        bh_page = int(request.args.get("bh_page", "1"))
    except Exception:
        bh_page = 1
    if bh_page < 1:
        bh_page = 1
    bh_q = Collaborator.query.order_by(Collaborator.name.asc())
    if bh_collab_id:
        bh_q = bh_q.filter(Collaborator.id == bh_collab_id)
    bh_all = bh_q.all()
    bh_total_pages = max(1, (len(bh_all) + per_page - 1) // per_page)
    if bh_page > bh_total_pages:
        bh_page = bh_total_pages
    bh_start = (bh_page - 1) * per_page
    bh_end = bh_start + per_page
    colaboradores_page = bh_all[bh_start:bh_end]
    # Créditos de Folga
    try:
        lc_collab_id = request.args.get("lc_collaborator_id", type=int)
    except Exception:
        lc_collab_id = None
    try:
        lc_page = int(request.args.get("lc_page", "1"))
    except Exception:
        lc_page = 1
    if lc_page < 1:
        lc_page = 1
    lc_q = TimeOffRecord.query.filter(TimeOffRecord.record_type == "folga_adicional").order_by(
        TimeOffRecord.date.desc()
    )
    if lc_collab_id:
        lc_q = lc_q.filter(TimeOffRecord.collaborator_id == lc_collab_id)
    leave_credits_all = lc_q.all()
    lc_total_pages = max(1, (len(leave_credits_all) + per_page - 1) // per_page)
    if lc_page > lc_total_pages:
        lc_page = lc_total_pages
    lc_start = (lc_page - 1) * per_page
    lc_end = lc_start + per_page
    leave_credits_page = leave_credits_all[lc_start:lc_end]
    # Uso de Folgas
    try:
        la_collab_id = request.args.get("la_collaborator_id", type=int)
    except Exception:
        la_collab_id = None
    try:
        la_page = int(request.args.get("la_page", "1"))
    except Exception:
        la_page = 1
    if la_page < 1:
        la_page = 1
    la_q = TimeOffRecord.query.filter(TimeOffRecord.record_type == "folga_usada").order_by(TimeOffRecord.date.desc())
    if la_collab_id:
        la_q = la_q.filter(TimeOffRecord.collaborator_id == la_collab_id)
    leave_assignments_all = la_q.all()
    la_total_pages = max(1, (len(leave_assignments_all) + per_page - 1) // per_page)
    if la_page > la_total_pages:
        la_page = la_total_pages
    la_start = (la_page - 1) * per_page
    la_end = la_start + per_page
    leave_assignments_page = leave_assignments_all[la_start:la_end]
    # VPS Storage
    vps_storage = None
    try:
        root = str(current_app.root_path or os.getcwd())
        du = shutil.disk_usage(root)
        uptime_str = None
        try:
            with open("/proc/uptime", "r") as f:
                secs = float((f.read().split()[0] or "0").strip())
            days = int(secs // 86400)
            rem = secs % 86400
            hours = int(rem // 3600)
            minutes = int((rem % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"
        except Exception:
            try:
                out = subprocess.check_output(["uptime", "-p"], timeout=2)
                uptime_str = (out.decode("utf-8", errors="ignore") or "").strip()
            except Exception:
                uptime_str = None
        load_str = None
        try:
            import os as _os

            la_fn = getattr(_os, "getloadavg", None)
            if callable(la_fn):
                lv = cast(Sequence[float], la_fn())
                try:
                    a = float(lv[0])
                    b = float(lv[1])
                    c = float(lv[2])
                    load_str = f"{a:.2f}, {b:.2f}, {c:.2f}"
                except Exception:
                    load_str = None
            else:
                try:
                    with open("/proc/loadavg", "r") as f:
                        parts = f.read().split()
                        it = iter(parts)
                        a = next(it, None)
                        b = next(it, None)
                        c = next(it, None)
                        if a is not None and b is not None and c is not None:
                            try:
                                aa = float(a)
                                bb = float(b)
                                cc = float(c)
                                load_str = f"{aa:.2f}, {bb:.2f}, {cc:.2f}"
                            except Exception:
                                load_str = None
                except Exception:
                    load_str = None
        except Exception:
            load_str = None

        def _fmt_bytes(n: int) -> str:
            units = ["B", "KB", "MB", "GB", "TB", "PB"]
            f = float(n)
            for u in units:
                if f < 1024.0:
                    return f"{f:.1f} {u}"
                f = f / 1024.0
            return f"{f:.1f} EB"

        vps_storage = {
            "total": du.total,
            "used": du.used,
            "free": du.free,
            "total_str": _fmt_bytes(du.total),
            "used_str": _fmt_bytes(du.used),
            "free_str": _fmt_bytes(du.free),
            "used_pct": int((du.used / du.total) * 100) if du.total > 0 else 0,
            "uptime_str": uptime_str,
            "load_str": load_str,
        }
    except Exception:
        vps_storage = None
    # Removido endereço de acesso (url/qr), mantendo somente dados necessários
    # Férias e Atestados foram movidos para jornada.py

    return render_template(
        "gestao.html",
        active_page="gestao",
        logs_page=logs_page,
        l_page=l_page,
        l_total_pages=l_total_pages,
        users_page=users_page,
        u_page=u_page,
        u_total_pages=u_total_pages,
        q=q,
        view=view,
        senha_sugestao=senha_sugestao,
        roles=roles,
        colaboradores=colaboradores,
        folgas=folgas,
        users=all_users,
        bank_balances=bank_balances,
        recent_entries=recent_entries,
        access_page=access_page,
        acc_page=acc_page,
        acc_total_pages=acc_total_pages,
        acc_user=acc_user,
        saldo_collab=saldo_collab,
        saldo_hours=saldo_hours,
        saldo_days=saldo_days,
        saldo_items=saldo_items,
        saldo_start=saldo_start,
        saldo_end=saldo_end,
        vps_storage=vps_storage,
        colaboradores_page=colaboradores_page,
        bh_page=bh_page,
        bh_total_pages=bh_total_pages,
        bh_collab_id=bh_collab_id,
        leave_credits_page=leave_credits_page,
        lc_page=lc_page,
        lc_total_pages=lc_total_pages,
        lc_collab_id=lc_collab_id,
        leave_assignments_page=leave_assignments_page,
        la_page=la_page,
        la_total_pages=la_total_pages,
        la_collab_id=la_collab_id,
    )


@bp.route("/gestao/colaboradores/criar", methods=["POST"])
@login_required
def gestao_colabs_criar():
    """Cria colaborador e usuário juntos (são uma coisa só)"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para criar colaboradores.", "danger")
        return redirect(url_for("usuarios.gestao"))
    nome = request.form.get("name", "").strip()
    cargo = request.form.get("role", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    nivel = request.form.get("nivel", "visualizador").strip()

    # Validação básica
    if not nome:
        flash("Nome é obrigatório.", "danger")
        return redirect(url_for("usuarios.gestao"))

    try:
        # Criar colaborador
        c = Collaborator()
        c.name = nome
        c.role = cargo
        c.active = True
        c.regular_team = request.form.get("regular_team", "").strip() or None
        c.sunday_team = request.form.get("sunday_team", "").strip() or None
        c.special_team = request.form.get("special_team", "").strip() or None

        # Se username foi fornecido, criar usuário também
        if username:
            if not password:
                flash("Senha é obrigatória quando criar usuário.", "danger")
                return redirect(url_for("usuarios.gestao"))

            # Normalizar username (apenas letras e números, minúsculas)
            username_normalized = "".join(ch for ch in username.lower() if ch.isalnum())
            if not username_normalized:
                flash("Login deve conter pelo menos uma letra ou número.", "danger")
                return redirect(url_for("usuarios.gestao"))

            # Verificar se username já existe
            if User.query.filter_by(username=username_normalized).first():
                flash(f'Login "{username_normalized}" já existe. Escolha outro.', "danger")
                return redirect(url_for("usuarios.gestao"))

            # Apenas DEV pode criar usuários com nível admin/DEV
            if nivel in ("admin", "DEV") and current_user.nivel != "DEV":
                flash("Apenas desenvolvedores podem criar usuários com nível Gerente ou Desenvolvedor.", "danger")
                return redirect(url_for("usuarios.gestao"))

            # Criar usuário
            u = User()
            u.name = nome
            u.username = username_normalized
            u.password_hash = generate_password_hash(password)
            u.nivel = nivel
            db.session.add(u)
            db.session.flush()  # Para obter o ID do usuário

            # Associar colaborador ao usuário
            c.user_id = u.id

        db.session.add(c)
        db.session.commit()

        if username:
            flash(f'Colaborador/Usuário "{nome}" criado com login "{username_normalized}".', "success")
        else:
            flash(f'Colaborador "{nome}" criado (sem usuário).', "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar colaborador: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/colaboradores/<int:id>/editar", methods=["POST"])
@login_required
def gestao_colabs_editar(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para editar colaboradores.", "danger")
        return redirect(url_for("usuarios.gestao"))
    c = Collaborator.query.get_or_404(id)
    try:
        c.name = ((request.form.get("name") or c.name or "").strip()) or c.name
        role_in = request.form.get("role")
        c.role = ((role_in or c.role or "").strip()) or None
        active_str = request.form.get("active", "on") or "on"
        c.active = True if active_str.lower() in ("on", "true", "1") else False
        rt_in = request.form.get("regular_team") or (c.regular_team or "")
        st_in = request.form.get("sunday_team") or (c.sunday_team or "")
        xt_in = request.form.get("special_team") or (c.special_team or "")
        c.regular_team = (rt_in.strip() or None) if (rt_in.strip() in ("1", "2")) else None
        c.sunday_team = (st_in.strip() or None) if (st_in.strip() in ("1", "2")) else None
        c.special_team = (xt_in.strip() or None) if (xt_in.strip() in ("1", "2")) else None

        # Gerenciar usuário (User e Collaborator são uma coisa só)
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        nivel = request.form.get("nivel", "").strip()

        if username:
            # Verificar se já existe usuário
            if c.user_id:
                u = User.query.get(c.user_id)
                if u:
                    # Apenas DEV pode alterar nível para admin/DEV
                    if nivel and nivel in ("admin", "DEV") and current_user.nivel != "DEV":
                        flash(
                            "Apenas desenvolvedores podem alterar usuários para nível Gerente ou Desenvolvedor.",
                            "danger",
                        )
                        return redirect(url_for("usuarios.gestao"))

                    # Atualizar usuário existente
                    u.name = c.name
                    # Verificar se username mudou
                    if u.username != username:
                        if User.query.filter(User.username == username, User.id != u.id).first():
                            flash(f'Login "{username}" já existe.', "danger")
                            return redirect(url_for("usuarios.gestao"))
                        u.username = username
                    if password:
                        u.password_hash = generate_password_hash(password)
                    if nivel:
                        u.nivel = nivel
                else:
                    # Criar novo usuário
                    if User.query.filter_by(username=username).first():
                        flash(f'Login "{username}" já existe.', "danger")
                        return redirect(url_for("usuarios.gestao"))

                    # Apenas DEV pode criar usuários com nível admin/DEV
                    nivel_final = nivel or "visualizador"
                    if nivel_final in ("admin", "DEV") and current_user.nivel != "DEV":
                        flash(
                            "Apenas desenvolvedores podem criar usuários com nível Gerente ou Desenvolvedor.", "danger"
                        )
                        return redirect(url_for("usuarios.gestao"))

                    u = User()
                    u.name = c.name
                    u.username = username
                    u.password_hash = generate_password_hash(password) if password else generate_password_hash("123456")
                    u.nivel = nivel_final
                    db.session.add(u)
                    db.session.flush()
                    c.user_id = u.id
            else:
                # Criar novo usuário
                if User.query.filter_by(username=username).first():
                    flash(f'Login "{username}" já existe.', "danger")
                    return redirect(url_for("usuarios.gestao"))

                # Apenas DEV pode criar usuários com nível admin/DEV
                nivel_final = nivel or "visualizador"
                if nivel_final in ("admin", "DEV") and current_user.nivel != "DEV":
                    flash("Apenas desenvolvedores podem criar usuários com nível Gerente ou Desenvolvedor.", "danger")
                    return redirect(url_for("usuarios.gestao"))

                u = User()
                u.name = c.name
                u.username = username
                u.password_hash = generate_password_hash(password) if password else generate_password_hash("123456")
                u.nivel = nivel_final
                db.session.add(u)
                db.session.flush()
                c.user_id = u.id

        db.session.commit()
        flash("Colaborador atualizado.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar colaborador: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/colaboradores/<int:id>/excluir", methods=["POST"])
@login_required
def gestao_colabs_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir colaboradores.", "danger")
        return redirect(url_for("usuarios.gestao"))
    c = Collaborator.query.get_or_404(id)
    try:
        Shift.query.filter_by(collaborator_id=c.id).delete()
        db.session.delete(c)
        db.session.commit()
        flash("Colaborador excluído.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir colaborador: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/usuarios/associar", methods=["POST"])
@login_required
def gestao_usuarios_associar():
    """Rota de compatibilidade - User e Collaborator são uma coisa só, não precisa associar"""
    flash("User e Collaborator são uma coisa só. Use o modal de edição para criar usuário para um colaborador.", "info")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/colaboradores/horas/adicionar", methods=["POST"])
@login_required
def gestao_colabs_horas_adicionar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para registrar horas.", "danger")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    hours_str = request.form.get("hours", "0").strip() or "0"
    reason = request.form.get("reason", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        h = float(hours_str)
    except Exception:
        flash("Dados inválidos para banco de horas.", "warning")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))
    try:
        e = TimeOffRecord()
        e.collaborator_id = cid
        e.date = d
        e.record_type = "horas"
        e.hours = h
        e.notes = reason
        e.origin = "manual"
        e.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(e)
        db.session.commit()
        try:
            from sqlalchemy import func

            total_hours = (
                db.session.query(func.coalesce(func.sum(TimeOffRecord.hours), 0.0))
                .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "horas")
                .scalar()
                or 0.0
            )
            total_hours = float(total_hours)
            auto_credits = (
                db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                .filter(
                    TimeOffRecord.collaborator_id == cid,
                    TimeOffRecord.record_type == "folga_adicional",
                    TimeOffRecord.origin == "horas",
                )
                .scalar()
                or 0
            )
            auto_credits = int(auto_credits)
            desired_credits = int(total_hours // 8.0)
            missing = max(0, desired_credits - auto_credits)
            if missing > 0:
                from datetime import date as _date

                for _ in range(missing):
                    lc = TimeOffRecord()
                    lc.collaborator_id = cid
                    lc.date = _date.today()
                    lc.record_type = "folga_adicional"
                    lc.days = 1
                    lc.origin = "horas"
                    lc.notes = "Crédito automático por 8h no banco de horas"
                    lc.created_by = "sistema"
                    db.session.add(lc)
                for _ in range(missing):
                    adj = TimeOffRecord()
                    adj.collaborator_id = cid
                    adj.date = _date.today()
                    adj.record_type = "horas"
                    adj.hours = -8.0
                    adj.notes = "Conversão automática: -8h por +1 dia de folga"
                    adj.origin = "sistema"
                    adj.created_by = "sistema"
                    db.session.add(adj)
                db.session.commit()
                flash(
                    f"Horas registradas. Conversão automática aplicada: +{missing} dia(s) e -{missing*8}h no banco.",
                    "success",
                )
            else:
                flash("Horas registradas.", "success")
        except Exception:
            flash("Horas registradas.", "success")
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar horas: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="colaboradores"))


@bp.route("/gestao/colaboradores/horas/verificar-conversao", methods=["POST"])
@login_required
def gestao_colabs_horas_verificar_conversao():
    """Verifica e aplica conversão automática de horas para dias, respeitando limites"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para executar esta ação.", "danger")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))

    collaborator_id = request.form.get("collaborator_id", type=int)
    if not collaborator_id:
        flash("Colaborador não especificado.", "warning")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))

    collaborator = Collaborator.query.get(collaborator_id)
    if not collaborator:
        flash("Colaborador não encontrado.", "danger")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))

    try:
        from datetime import date as _date

        from sqlalchemy import func

        # 1. Calcular total BRUTO de horas (somando apenas horas positivas, sem considerar conversões negativas)
        total_bruto_hours = float(
            db.session.query(
                func.coalesce(func.sum(func.case((TimeOffRecord.hours > 0, TimeOffRecord.hours), else_=0)), 0.0)
            )
            .filter(TimeOffRecord.collaborator_id == collaborator_id, TimeOffRecord.record_type == "horas")
            .scalar()
            or 0.0
        )

        # 2. Calcular quantos dias já foram gerados automaticamente (origin='horas')
        auto_credits = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(
                TimeOffRecord.collaborator_id == collaborator_id,
                TimeOffRecord.record_type == "folga_adicional",
                TimeOffRecord.origin == "horas",
            )
            .scalar()
            or 0
        )
        auto_credits = int(auto_credits)

        # 3. Calcular quantos dias deveriam ser gerados (total_bruto_horas // 8)
        desired_credits = int(total_bruto_hours // 8.0) if total_bruto_hours >= 0.0 else 0

        # 4. Calcular quantos dias faltam gerar
        missing_credits = max(0, desired_credits - auto_credits)

        if missing_credits == 0:
            flash(
                f"Nenhuma conversão necessária. O colaborador {collaborator.name} já tem todas as horas convertidas em dias (total bruto: {total_bruto_hours:.2f}h = {desired_credits} dia(s) já convertido(s)).",
                "info",
            )
            return redirect(url_for("usuarios.gestao", view="colaboradores", saldo_collaborator_id=collaborator_id))

        # 5. Calcular dias totais que o colaborador já tem (todos os créditos)
        total_credits = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == collaborator_id, TimeOffRecord.record_type == "folga_adicional")
            .scalar()
            or 0
        )
        total_credits = int(total_credits)

        # 6. Calcular folgas já usadas
        used_days = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == collaborator_id, TimeOffRecord.record_type == "folga_usada")
            .scalar()
            or 0
        )
        used_days = int(used_days)

        # 7. Calcular dias convertidos em dinheiro
        converted_days = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == collaborator_id, TimeOffRecord.record_type == "conversao")
            .scalar()
            or 0
        )
        converted_days = int(converted_days)

        # 8. Calcular saldo atual (antes da conversão)
        current_balance = total_credits - used_days - converted_days

        # 9. Calcular saldo final após conversão
        final_balance = current_balance + missing_credits

        # 10. Verificar limite máximo (padrão: 30 dias, pode ser configurável)
        max_allowed_days = 30  # Limite padrão de dias permitidos
        max_balance = max_allowed_days

        if final_balance > max_balance:
            # Ajustar para não ultrapassar o limite
            allowed_credits = max(0, max_balance - current_balance)
            if allowed_credits == 0:
                flash(
                    f"Limite de {max_allowed_days} dias atingido para {collaborator.name}. "
                    f"Saldo atual: {current_balance} dias. Não é possível adicionar mais dias.",
                    "warning",
                )
                return redirect(url_for("usuarios.gestao", view="colaboradores", saldo_collaborator_id=collaborator_id))

            missing_credits = allowed_credits
            flash(
                f"Atenção: A conversão foi limitada a {allowed_credits} dia(s) para não ultrapassar o limite de {max_allowed_days} dias. "
                f"Saldo atual: {current_balance} dias, após conversão: {current_balance + allowed_credits} dias.",
                "warning",
            )

        # 11. Aplicar conversão
        converted_count = 0
        for _ in range(missing_credits):
            # Criar crédito de folga
            lc = TimeOffRecord()
            lc.collaborator_id = collaborator_id
            lc.date = _date.today()
            lc.record_type = "folga_adicional"
            lc.days = 1
            lc.origin = "horas"
            lc.notes = "Conversão automática verificada: 8h convertidas em 1 dia de folga"
            lc.created_by = "sistema"
            db.session.add(lc)

            # Ajustar banco de horas (-8h)
            adj = TimeOffRecord()
            adj.collaborator_id = collaborator_id
            adj.date = _date.today()
            adj.record_type = "horas"
            adj.hours = -8.0
            adj.notes = "Conversão automática verificada: -8h por +1 dia de folga"
            adj.origin = "sistema"
            adj.created_by = "sistema"
            db.session.add(adj)
            converted_count += 1

        db.session.commit()

        # Recalcular saldo final
        new_total_credits = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == collaborator_id, TimeOffRecord.record_type == "folga_adicional")
            .scalar()
            or 0
        )
        new_balance = int(new_total_credits) - used_days - converted_days

        flash(
            f"✅ Conversão aplicada com sucesso para {collaborator.name}! "
            f"{converted_count} dia(s) convertido(s) de {total_bruto_hours:.2f}h brutas. "
            f"Saldo final: {new_balance} dia(s) e {total_bruto_hours % 8.0:.2f}h restantes.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao verificar e aplicar conversão: {e}", "danger")

    return redirect(url_for("usuarios.gestao", view="colaboradores", saldo_collaborator_id=collaborator_id))


@bp.route("/gestao/colaboradores/horas/excluir/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_horas_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir lançamentos.", "danger")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))
    e = TimeOffRecord.query.filter(TimeOffRecord.id == id, TimeOffRecord.record_type == "horas").first_or_404()
    try:
        cid = int(e.collaborator_id or 0)
        db.session.delete(e)
        db.session.commit()
        try:
            from sqlalchemy import func

            total_hours = (
                db.session.query(func.coalesce(func.sum(TimeOffRecord.hours), 0.0))
                .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "horas")
                .scalar()
                or 0.0
            )
            total_hours = float(total_hours)
            auto_credits = (
                db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
                .filter(
                    TimeOffRecord.collaborator_id == cid,
                    TimeOffRecord.record_type == "folga_adicional",
                    TimeOffRecord.origin == "horas",
                )
                .scalar()
                or 0
            )
            auto_credits = int(auto_credits)
            desired_credits = int(total_hours // 8.0)
            if auto_credits > desired_credits:
                excess = auto_credits - desired_credits
                to_delete_credits = (
                    TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == cid,
                        TimeOffRecord.record_type == "folga_adicional",
                        TimeOffRecord.origin == "horas",
                    )
                    .order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc())
                    .limit(excess)
                    .all()
                )
                for lc in to_delete_credits:
                    db.session.delete(lc)
                to_delete_adjusts = (
                    TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == cid,
                        TimeOffRecord.record_type == "horas",
                        TimeOffRecord.hours == -8.0,
                        TimeOffRecord.notes.like("Conversão automática:%"),
                    )
                    .order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc())
                    .limit(excess)
                    .all()
                )
                for adj in to_delete_adjusts:
                    db.session.delete(adj)
                db.session.commit()
                removed_adj = len(to_delete_adjusts)
                if removed_adj < excess:
                    missing_adj = excess - removed_adj
                    from datetime import date as _date

                    for _ in range(missing_adj):
                        comp = TimeOffRecord()
                        comp.collaborator_id = cid
                        comp.date = _date.today()
                        comp.record_type = "horas"
                        comp.hours = 8.0
                        comp.notes = "Reversão automática: +8h pela exclusão de crédito por horas"
                        comp.origin = "sistema"
                        comp.created_by = "sistema"
                        db.session.add(comp)
                    db.session.commit()
                flash(
                    f"Lançamento excluído. Conversões automáticas revertidas: -{excess} dia(s) e +{excess*8}h no banco.",
                    "warning",
                )
            elif auto_credits < desired_credits:
                missing = desired_credits - auto_credits
                from datetime import date as _date

                for _ in range(missing):
                    lc = TimeOffRecord()
                    lc.collaborator_id = cid
                    lc.date = _date.today()
                    lc.record_type = "folga_adicional"
                    lc.days = 1
                    lc.origin = "horas"
                    lc.notes = "Crédito automático por 8h no banco de horas (ajuste pós-exclusão)"
                    lc.created_by = "sistema"
                    db.session.add(lc)
                for _ in range(missing):
                    adj = TimeOffRecord()
                    adj.collaborator_id = cid
                    adj.date = _date.today()
                    adj.record_type = "horas"
                    adj.hours = -8.0
                    adj.notes = "Conversão automática: -8h por +1 dia de folga (ajuste pós-exclusão)"
                    adj.origin = "sistema"
                    adj.created_by = "sistema"
                    db.session.add(adj)
                db.session.commit()
                flash(
                    f"Lançamento excluído. Conversões automáticas ajustadas: +{missing} dia(s) e -{missing*8}h no banco.",
                    "info",
                )
            else:
                flash("Lançamento excluído.", "success")
        except Exception:
            flash("Lançamento excluído.", "success")
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao excluir lançamento: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="colaboradores"))


@bp.route("/gestao/colaboradores/horas/editar/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_horas_editar(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode editar lançamentos.", "danger")
        return redirect(url_for("usuarios.gestao", view="colaboradores"))
    e = TimeOffRecord.query.filter(TimeOffRecord.id == id, TimeOffRecord.record_type == "horas").first_or_404()
    date_str = request.form.get("date", "").strip() or ""
    hours_str = request.form.get("hours", "0").strip() or "0"
    reason = request.form.get("reason", "").strip() or ""
    try:
        if date_str:
            e.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        e.hours = float(hours_str)
        e.notes = reason
        db.session.commit()
        flash("Lançamento de horas atualizado.", "info")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao editar lançamento: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="colaboradores"))


@bp.route("/gestao/colaboradores/folgas/credito/adicionar", methods=["POST"])
@login_required
def gestao_colabs_folga_credito_adicionar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para registrar folgas.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("amount_days", "1").strip() or "1"
    origin = request.form.get("origin", "manual").strip() or "manual"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = int(days_str)
    except Exception:
        flash("Dados inválidos para crédito de folga.", "warning")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    try:
        lc = TimeOffRecord()
        lc.collaborator_id = cid
        lc.date = d
        lc.record_type = "folga_adicional"
        lc.days = days
        lc.origin = origin
        lc.notes = notes
        lc.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(lc)
        db.session.commit()
        flash(f"Crédito de {days} dia(s) de folga registrado.", "success")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao registrar crédito: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/colaboradores/folgas/credito/editar/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_folga_credito_editar(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode editar créditos de folga.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    lc = TimeOffRecord.query.filter(
        TimeOffRecord.id == id, TimeOffRecord.record_type == "folga_adicional"
    ).first_or_404()
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("amount_days", "").strip() or ""
    notes = request.form.get("notes", "").strip() or ""
    try:
        if date_str:
            lc.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if days_str:
            lc.amount_days = int(days_str)
        lc.notes = notes
        db.session.commit()
        flash("Crédito de folga atualizado.", "info")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao editar crédito: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/colaboradores/folgas/credito/excluir/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_folga_credito_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir créditos de folga.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    lc = TimeOffRecord.query.filter(
        TimeOffRecord.id == id, TimeOffRecord.record_type == "folga_adicional"
    ).first_or_404()
    try:
        db.session.delete(lc)
        db.session.commit()
        flash("Crédito de folga excluído.", "danger")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao excluir crédito: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/colaboradores/folgas/uso/adicionar", methods=["POST"])
@login_required
def gestao_colabs_folga_uso_adicionar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para registrar uso de folgas.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days_used", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or ""
    try:
        from datetime import timedelta

        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = int(days_str)
    except Exception:
        flash("Dados inválidos para uso de folga.", "warning")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    try:
        try:
            end_d = d + timedelta(days=max(1, days) - 1)
            feriados_no_periodo = Holiday.query.filter(Holiday.date >= d, Holiday.date <= end_d).count()
        except Exception:
            feriados_no_periodo = 0
        effective_days = max(0, int(days) - int(feriados_no_periodo))

        from sqlalchemy import func

        credits_sum = int(
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_adicional")
            .scalar()
            or 0
        )
        assigned_sum = int(
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_usada")
            .scalar()
            or 0
        )
        converted_sum = int(
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "conversao")
            .scalar()
            or 0
        )
        saldo_days = credits_sum - assigned_sum - converted_sum

        if effective_days < 1 or effective_days > saldo_days:
            flash("Saldo insuficiente de folgas.", "warning")
            return redirect(url_for("usuarios.gestao", view="folgas"))

        la = TimeOffRecord()
        la.collaborator_id = cid
        la.date = d
        la.record_type = "folga_usada"
        la.days = effective_days
        la.notes = notes
        la.origin = "manual"
        la.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(la)
        db.session.commit()
        flash(f"Uso de {effective_days} dia(s) de folga registrado.", "success")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao registrar uso: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/colaboradores/folgas/uso/editar/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_folga_uso_editar(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode editar uso de folga.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    la = TimeOffRecord.query.filter(TimeOffRecord.id == id, TimeOffRecord.record_type == "folga_usada").first_or_404()
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days_used", "").strip() or ""
    notes = request.form.get("notes", "").strip() or ""
    try:
        from datetime import timedelta

        if date_str:
            la.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        # recalcular dias efetivos desconsiderando feriados
        if days_str:
            try:
                new_days = int(days_str)
                end_d = la.date + timedelta(days=max(1, new_days) - 1)
                feriados_no_periodo = Holiday.query.filter(Holiday.date >= la.date, Holiday.date <= end_d).count()
            except Exception:
                feriados_no_periodo = 0
            la.days = max(0, int(new_days) - int(feriados_no_periodo))
        la.notes = notes
        db.session.commit()
        flash("Uso de folga atualizado.", "info")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao editar uso: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/colaboradores/folgas/uso/excluir/<int:id>", methods=["POST"])
@login_required
def gestao_colabs_folga_uso_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir uso de folga.", "danger")
        return redirect(url_for("usuarios.gestao", view="folgas"))
    la = TimeOffRecord.query.filter(TimeOffRecord.id == id, TimeOffRecord.record_type == "folga_usada").first_or_404()
    try:
        db.session.delete(la)
        db.session.commit()
        flash("Uso de folga excluído.", "danger")
    except Exception as ex:
        db.session.rollback()
        flash(f"Erro ao excluir uso: {ex}", "danger")
    return redirect(url_for("usuarios.gestao", view="folgas"))


@bp.route("/gestao/roles", methods=["POST"])
@login_required
def gestao_role_criar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("usuarios.gestao"))
    name = (request.form.get("name") or "").strip()
    nivel = (request.form.get("nivel") or "visualizador").strip()
    if not name:
        flash("Nome do cargo é obrigatório.", "warning")
        return redirect(url_for("usuarios.gestao"))
    if nivel not in ("visualizador", "operador", "admin"):
        flash("Tipo de permissão inválido.", "warning")
        return redirect(url_for("usuarios.gestao"))
    if JobRole.query.filter_by(name=name).first() is not None:
        flash("Cargo já existe.", "danger")
        return redirect(url_for("usuarios.gestao"))
    try:
        r = JobRole()
        r.name = name
        r.nivel = nivel
        db.session.add(r)
        db.session.commit()
        flash("Cargo criado.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar cargo: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/roles/<int:id>/editar", methods=["POST"])
@login_required
def gestao_role_editar(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("usuarios.gestao"))
    role = JobRole.query.get_or_404(id)
    name = (request.form.get("name") or role.name).strip()
    nivel = (request.form.get("nivel") or role.nivel).strip()
    if nivel not in ("visualizador", "operador", "admin"):
        flash("Tipo de permissão inválido.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        role.name = name
        role.nivel = nivel
        db.session.commit()
        flash("Cargo atualizado.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar cargo: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/roles/<int:id>/excluir", methods=["POST"])
@login_required
def gestao_role_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("usuarios.gestao"))
    role = JobRole.query.get_or_404(id)
    try:
        db.session.delete(role)
        db.session.commit()
        flash("Cargo excluído.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir cargo: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


# Rotas de férias e atestados foram movidas para jornada.py
