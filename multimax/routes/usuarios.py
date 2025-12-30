from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from ..password_hash import generate_password_hash, check_password_hash
from ..filename_utils import secure_filename
from .. import db
from ..models import User, Produto, Historico, CleaningHistory, SystemLog, NotificationRead, HourBankEntry, Collaborator, JobRole, LeaveCredit, LeaveAssignment, LeaveConversion, Shift, CleaningTask, Vacation, MedicalCertificate, Holiday
from datetime import datetime
from typing import cast, Sequence
import os
 
import threading
import time
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path


bp = Blueprint('usuarios', __name__)

def _is_dev(user):
    """Verifica se o usuário é desenvolvedor (acesso total)"""
    return user.nivel == 'DEV'

def _can_manage_admins(user):
    """Verifica se o usuário pode gerenciar administradores (apenas DEV)"""
    return user.nivel == 'DEV'

def _block_viewer_modifications():
    """Bloqueia visualizadores de fazer qualquer alteração (exceto perfil)"""
    if current_user.nivel == 'visualizador':
        flash('Visualizadores não têm permissão para fazer alterações no sistema.', 'danger')
        return True
    return False

@bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Gerente pode gerenciar usuários.', 'danger')
        return redirect(url_for('estoque.index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nivel = request.form.get('nivel', 'visualizador').strip()
        # Apenas DEV pode criar ou alterar usuários para admin/DEV
        if nivel in ('admin', 'DEV') and current_user.nivel != 'DEV':
            flash('Apenas o desenvolvedor pode criar ou alterar administradores.', 'danger')
            return redirect(url_for('usuarios.gestao'))
        if not name or not password:
            flash('Nome e senha são obrigatórios.', 'warning')
            return redirect(url_for('usuarios.gestao'))
        if username_input:
            base_username = ''.join(ch for ch in username_input.lower() if ch.isalnum()) or 'user'
            username = base_username
            if User.query.filter_by(username=username).first() is not None:
                flash('Login já existe. Escolha outro.', 'danger')
                return redirect(url_for('usuarios.gestao'))
        else:
            base_username = ''.join(ch for ch in name.lower() if ch.isalnum()) or 'user'
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
            log.origem = 'Usuarios'
            log.evento = 'criar'
            log.detalhes = f'Criado {name} ({username}) nivel {nivel}'
            log.usuario = current_user.name
            db.session.add(log)
            db.session.commit()
            flash(f'Usuário "{name}" criado com login "{username}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {e}', 'danger')
        return redirect(url_for('usuarios.gestao'))
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/vps/restart', methods=['POST'])
@login_required
def gestao_vps_restart():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem reiniciar a VPS.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    secret_in = (request.form.get('secret_key') or '').strip()
    secret_cfg = str(current_app.config.get('SECRET_KEY') or '').strip()
    if not secret_in or secret_in != secret_cfg:
        flash('Senha inválida para reiniciar a VPS.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        cmd = (os.getenv('VPS_REBOOT_CMD') or 'sudo reboot').strip()
        subprocess.Popen(cmd, shell=True)
        flash('Reinício da VPS iniciado.', 'warning')
    except Exception as e:
        flash(f'Falha ao reiniciar VPS: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/vps/upload', methods=['POST'])
@login_required
def gestao_vps_upload():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem atualizar a VPS.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    secret_in = (request.form.get('secret_key') or '').strip()
    secret_cfg = str(current_app.config.get('SECRET_KEY') or '').strip()
    if not secret_in or secret_in != secret_cfg:
        flash('Senha inválida para atualizar a VPS.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    file = request.files.get('zipfile')
    if not file or not (file.filename or '').lower().endswith('.zip'):
        flash('Selecione um arquivo .zip válido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    tmp_dir = tempfile.mkdtemp(prefix='mmx_up_')
    zip_path = os.path.join(tmp_dir, 'update.zip')
    try:
        file.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
        root = Path(current_app.root_path).resolve()
        extracted_root = Path(tmp_dir).resolve()
        copied = 0
        for p in extracted_root.rglob('*'):
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
        setup_script = (root / 'vps_setup.sh')
        alt_setup_script = (root / 'scripts' / 'vps_setup.sh')
        run_script = setup_script if setup_script.exists() else alt_setup_script
        if run_script.exists():
            try:
                subprocess.Popen(['bash', str(run_script)], cwd=str(root))
            except Exception:
                pass
        try:
            cmd = (os.getenv('VPS_REBOOT_CMD') or 'sudo reboot').strip()
            subprocess.Popen(cmd, shell=True)
        except Exception:
            pass
        flash(f'Atualização aplicada ({copied} arquivos). VPS será reiniciada.', 'success')
    except Exception as e:
        flash(f'Falha ao aplicar atualização: {e}', 'danger')
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/restart', methods=['POST'])
@login_required
def gestao_restart():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem reiniciar.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    secret_in = (request.form.get('secret_key') or '').strip()
    secret_cfg = str(current_app.config.get('SECRET_KEY') or '').strip()
    if not secret_in or secret_in != secret_cfg:
        flash('Senha inválida para reinício do sistema.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        cmd = (os.getenv('RESTART_CMD') or '').strip()
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
        flash('Reiniciando MultiMax na VPS...', 'warning')
    except Exception as e:
        flash(f'Falha ao iniciar reinício: {e}', 'danger')
    return redirect(url_for('home.index'))


@bp.route('/users/<int:user_id>/senha', methods=['POST'])
@login_required
def update_password(user_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para atualizar senhas.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        flash('Informe a nova senha.', 'warning')
        return redirect(url_for('usuarios.users'))
    try:
        user.password_hash = generate_password_hash(new_password)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'senha'
        log.detalhes = f'Senha atualizada para {user.username}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" atualizada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar senha: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/users/<int:user_id>/reset_senha', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para redefinir senhas.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    default_password = '123456'
    try:
        user.password_hash = generate_password_hash(default_password)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'senha'
        log.detalhes = f'Senha redefinida para {user.username}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Senha de "{user.name}" redefinida.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao redefinir senha: {e}', 'danger')
    return redirect(url_for('usuarios.users'))

@bp.route('/users/<int:user_id>/nivel', methods=['POST'])
@login_required
def update_level(user_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para alterar níveis de usuário.', 'danger')
        return redirect(url_for('estoque.index'))
    user = User.query.get_or_404(user_id)
    nivel = request.form.get('nivel', 'visualizador').strip()
    if nivel not in ('visualizador', 'operador', 'admin', 'DEV'):
        flash('Nível inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    # Apenas DEV pode alterar nível para admin/DEV
    if nivel in ('admin', 'DEV') and current_user.nivel != 'DEV':
        flash('Apenas o desenvolvedor pode alterar usuários para administrador.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        user.nivel = nivel
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'nivel'
        log.detalhes = f'Nivel {user.username} -> {nivel}'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Nivel do usuário "{user.name}" atualizado para "{nivel}".', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar nível: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/users/<int:user_id>/excluir', methods=['POST'])
@login_required
def excluir_user(user_id):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para excluir usuários.', 'danger')
        return redirect(url_for('estoque.index'))
    if current_user.id == user_id:
        flash('Você não pode excluir sua própria conta.', 'warning')
        return redirect(url_for('usuarios.users'))
    user = User.query.get_or_404(user_id)
    # Apenas DEV pode excluir administradores
    if user.nivel in ('admin', 'DEV') and current_user.nivel != 'DEV':
        flash('Apenas o desenvolvedor pode excluir administradores.', 'danger')
        return redirect(url_for('usuarios.users'))
    try:
        db.session.delete(user)
        log = SystemLog()
        log.origem = 'Usuarios'
        log.evento = 'excluir'
        log.detalhes = f'Excluido {user.name} ({user.username})'
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Usuário "{user.name}" excluído com sucesso.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('usuarios.users'))

@bp.route('/monitor')
@login_required
def monitor():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Administradores.', 'danger')
        return redirect(url_for('estoque.index'))
    return redirect(url_for('usuarios.gestao'))

@bp.route('/notifications/read')
@login_required
def notifications_read():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem resolver notificações.', 'danger')
        return redirect(url_for('home.index'))
    tipo = request.args.get('tipo')
    ref_id = request.args.get('id', type=int)
    nxt = request.args.get('next', url_for('estoque.index'))
    if tipo in ('estoque', 'limpeza') and ref_id:
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

@bp.route('/notifications/unread')
@login_required
def notifications_unread():
    tipo = request.args.get('tipo')
    ref_id = request.args.get('id', type=int)
    nxt = request.args.get('next', url_for('estoque.index'))
    if tipo in ('estoque', 'limpeza') and ref_id:
        try:
            NotificationRead.query.filter_by(user_id=current_user.id, tipo=tipo, ref_id=ref_id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(nxt)

@bp.route('/notifications/unread_all')
@login_required
def notifications_unread_all():
    nxt = request.args.get('next', url_for('estoque.index'))
    try:
        NotificationRead.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(nxt)

@bp.route('/notifications/read_all')
@login_required
def notifications_read_all():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Administradores podem resolver notificações.', 'danger')
        return redirect(url_for('home.index'))
    nxt = request.args.get('next', url_for('home.index'))
    try:
        crit = (
            Produto.query
            .filter(Produto.estoque_minimo.isnot(None), Produto.estoque_minimo > 0, Produto.quantidade <= Produto.estoque_minimo)
            .order_by(Produto.nome.asc())
            .limit(100)
            .all()
        )
        for p in crit:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo='estoque', ref_id=p.id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = 'estoque'
                nr.ref_id = p.id
                db.session.add(nr)
        from datetime import date as _date, timedelta as _td
        horizon = _date.today() + _td(days=3)
        tasks = (
            CleaningTask.query
            .filter(CleaningTask.proxima_data.isnot(None), CleaningTask.proxima_data <= horizon)
            .order_by(CleaningTask.proxima_data.asc())
            .limit(100)
            .all()
        )
        for t in tasks:
            if NotificationRead.query.filter_by(user_id=current_user.id, tipo='limpeza', ref_id=t.id).first() is None:
                nr = NotificationRead()
                nr.user_id = current_user.id
                nr.tipo = 'limpeza'
                nr.ref_id = t.id
                db.session.add(nr)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    return redirect(nxt)
@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        # Visualizadores podem alterar apenas nome e senha (não username)
        if current_user.nivel == 'visualizador':
            name = (request.form.get('name') or '').strip()
            if not name:
                flash('Nome é obrigatório.', 'warning')
                return redirect(url_for('usuarios.perfil'))
            current_user.name = name
        else:
            # Outros níveis podem alterar nome e username
            name = (request.form.get('name') or '').strip()
            username_input = (request.form.get('username') or '').strip().lower()
            if not name:
                flash('Nome é obrigatório.', 'warning')
                return redirect(url_for('usuarios.perfil'))
            if not username_input:
                flash('Login é obrigatório.', 'warning')
                return redirect(url_for('usuarios.perfil'))
            base_username = ''.join(ch for ch in username_input if ch.isalnum())
            if not base_username:
                flash('Login deve conter apenas letras e números.', 'warning')
                return redirect(url_for('usuarios.perfil'))
            if base_username != current_user.username:
                if User.query.filter_by(username=base_username).first() is not None:
                    flash('Login já existe. Escolha outro.', 'danger')
                    return redirect(url_for('usuarios.perfil'))
                current_user.username = base_username
            current_user.name = name
        try:
            db.session.commit()
            flash('Perfil atualizado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar perfil: {e}', 'danger')
        return redirect(url_for('usuarios.perfil'))
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        if 'user_id' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN user_id INTEGER'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    collab = None
    entries = []
    total = 0.0
    residual_hours = 0.0
    folga_balance = 0
    folga_credits = []
    folga_assigned = []
    folga_conversions = []
    try:
        collab = Collaborator.query.filter_by(user_id=current_user.id).first()
        if collab:
            try:
                from sqlalchemy import func
                total_pre = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == collab.id).scalar() or 0.0
                total_pre = float(total_pre)
                auto_credits_pre = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == collab.id, LeaveCredit.origin == 'horas').scalar() or 0
                auto_credits_pre = int(auto_credits_pre)
                desired_pre = int(total_pre // 8.0) if total_pre > 0.0 else 0
                missing_pre = max(0, desired_pre - auto_credits_pre)
                if missing_pre > 0:
                    from datetime import date as _date
                    for _ in range(missing_pre):
                        lc = LeaveCredit()
                        lc.collaborator_id = collab.id
                        lc.date = _date.today()
                        lc.amount_days = 1
                        lc.origin = 'horas'
                        lc.notes = 'Reconciliação automática: crédito por 8h acumuladas'
                        db.session.add(lc)
                    for _ in range(missing_pre):
                        adj = HourBankEntry()
                        adj.collaborator_id = collab.id
                        adj.date = _date.today()
                        adj.hours = -8.0
                        adj.reason = 'Reconciliação automática: -8h por +1 dia'
                        db.session.add(adj)
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
            entries = HourBankEntry.query.filter_by(collaborator_id=collab.id).order_by(HourBankEntry.date.desc()).limit(50).all()
            try:
                from sqlalchemy import func
                total = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == collab.id).scalar() or 0.0
                total = float(total)
                if total >= 0.0:
                    residual_hours = total % 8.0
                else:
                    residual_hours = - ((-total) % 8.0)
            except Exception:
                total = 0.0
                residual_hours = 0.0
            try:
                from sqlalchemy import func
                credits_sum = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == collab.id).scalar() or 0
                assigned_sum = db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == collab.id).scalar() or 0
                converted_sum = db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == collab.id).scalar() or 0
                folga_balance = int(credits_sum) - int(assigned_sum) - int(converted_sum)
            except Exception:
                folga_balance = 0
            try:
                folga_credits = LeaveCredit.query.filter_by(collaborator_id=collab.id).order_by(LeaveCredit.date.desc()).limit(50).all()
            except Exception:
                folga_credits = []
            try:
                folga_assigned = LeaveAssignment.query.filter_by(collaborator_id=collab.id).order_by(LeaveAssignment.date.desc()).limit(50).all()
            except Exception:
                folga_assigned = []
            try:
                folga_conversions = LeaveConversion.query.filter_by(collaborator_id=collab.id).order_by(LeaveConversion.date.desc()).limit(50).all()
            except Exception:
                folga_conversions = []
    except Exception:
        collab = None
        entries = []
        total = 0.0
    
    is_on_break = False
    is_on_vacation = False
    vacation_end_date = None
    vacation_end_timestamp = 0
    vacation_return_hour = '05:00'
    is_on_medical = False
    medical_end_timestamp = 0
    medical_end_date = None
    break_end_timestamp = 0
    next_shift_date = None
    next_shift_hour = None
    
    if collab:
        from datetime import date as _date, datetime as _dt, timedelta as _td
        today = _date.today()
        
        try:
            today_shift = Shift.query.filter_by(
                collaborator_id=collab.id,
                date=today
            ).first()
            if today_shift and ((today_shift.shift_type or '').lower() == 'folga' or (today_shift.turno or '').lower() == 'folga'):
                is_on_break = True
                end_dt = _dt.combine(today, _dt.min.time().replace(hour=23, minute=59, second=59))
                break_end_timestamp = int(end_dt.timestamp())
        except Exception:
            pass
        try:
            ns = Shift.query.filter(
                Shift.collaborator_id == collab.id,
                Shift.date >= today,
                Shift.shift_type != 'folga'
            ).order_by(Shift.date.asc()).first()
            if ns:
                next_shift_date = ns.date
                if ns.start_dt:
                    next_shift_hour = ns.start_dt.strftime('%H:%M')
                else:
                    st = (ns.shift_type or '').lower()
                    if st.startswith('abertura'):
                        next_shift_hour = '05:00'
                    elif st == 'fechamento':
                        next_shift_hour = '09:30'
                    elif st.startswith('domingo'):
                        next_shift_hour = '05:00'
                    else:
                        next_shift_hour = '05:00'
        except Exception:
            pass
        if not is_on_break:
            try:
                la_list = LeaveAssignment.query.filter(
                    LeaveAssignment.collaborator_id == collab.id,
                    LeaveAssignment.date <= today
                ).order_by(LeaveAssignment.date.desc()).limit(5).all()
                for la in (la_list or []):
                    days = max(1, int(la.days_used or 1))
                    end_date = la.date + _td(days=days - 1)
                    if end_date >= today:
                        is_on_break = True
                        end_dt = _dt.combine(end_date, _dt.min.time().replace(hour=23, minute=59, second=59))
                        break_end_timestamp = int(end_dt.timestamp())
                        break
            except Exception:
                pass
        
        try:
            vacation = Vacation.query.filter(
                Vacation.collaborator_id == collab.id,
                Vacation.data_inicio <= today,
                Vacation.data_fim >= today
            ).first()
            if vacation:
                is_on_vacation = True
                vacation_end_date = vacation.data_fim.strftime('%d/%m/%Y')
                
                return_date = vacation.data_fim + _td(days=1)
                
                try:
                    next_shift = Shift.query.filter(
                        Shift.collaborator_id == collab.id,
                        Shift.date >= return_date,
                        Shift.shift_type != 'folga'
                    ).order_by(Shift.date.asc()).first()
                    
                    if next_shift:
                        return_date = next_shift.date
                        if next_shift.start_dt:
                            try:
                                vacation_return_hour = next_shift.start_dt.strftime('%H:%M')
                            except Exception:
                                vacation_return_hour = '05:00'
                        else:
                            st = (next_shift.shift_type or '').lower()
                            if st.startswith('abertura'):
                                vacation_return_hour = '05:00'
                            elif st == 'fechamento':
                                vacation_return_hour = '09:30'
                            elif st.startswith('domingo'):
                                vacation_return_hour = '05:00'
                            else:
                                vacation_return_hour = '05:00'
                except Exception:
                    pass
                
                try:
                    hour_parts = vacation_return_hour.split(':')
                    return_hour = int(hour_parts[0]) if hour_parts else 5
                    return_min = int(hour_parts[1]) if len(hour_parts) > 1 else 0
                except Exception:
                    return_hour, return_min = 5, 0
                
                return_datetime = _dt.combine(return_date, _dt.min.time().replace(hour=return_hour, minute=return_min))
                vacation_end_timestamp = int(return_datetime.timestamp())
        except Exception:
            pass
        
        try:
            mc = MedicalCertificate.query.filter(
                MedicalCertificate.collaborator_id == collab.id,
                MedicalCertificate.data_inicio <= today,
                MedicalCertificate.data_fim >= today
            ).order_by(MedicalCertificate.data_fim.desc()).first()
            if mc:
                is_on_medical = True
                medical_end_date = mc.data_fim.strftime('%d/%m/%Y')
                med_end_dt = _dt.combine(mc.data_fim, _dt.min.time().replace(hour=23, minute=59, second=59))
                medical_end_timestamp = int(med_end_dt.timestamp())
        except Exception:
            pass
    
    return render_template('perfil.html', active_page='perfil', collab=collab, entries=entries, total=total, residual_hours=residual_hours, folga_balance=folga_balance, folga_credits=folga_credits, folga_assigned=folga_assigned, folga_conversions=folga_conversions, is_on_break=is_on_break, is_on_vacation=is_on_vacation, vacation_end_date=vacation_end_date, vacation_end_timestamp=vacation_end_timestamp, vacation_return_hour=vacation_return_hour, is_on_medical=is_on_medical, medical_end_timestamp=medical_end_timestamp, medical_end_date=medical_end_date, break_end_timestamp=break_end_timestamp, next_shift_date=next_shift_date, next_shift_hour=next_shift_hour)

@bp.route('/perfil/senha', methods=['POST'])
@login_required
def perfil_senha():
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar = request.form.get('confirmar_senha', '')
    if not nova_senha or len(nova_senha) < 6:
        flash('Nova senha deve ter ao menos 6 caracteres.', 'warning')
        return redirect(url_for('usuarios.perfil'))
    if nova_senha != confirmar:
        flash('Confirmação de senha não confere.', 'warning')
        return redirect(url_for('usuarios.perfil'))
    if not check_password_hash(current_user.password_hash or '', senha_atual):
        flash('Senha atual inválida.', 'danger')
        return redirect(url_for('usuarios.perfil'))
    try:
        current_user.password_hash = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha atualizada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar senha: {e}', 'danger')
    return redirect(url_for('usuarios.perfil'))

@bp.route('/gestao', methods=['GET'])
@login_required
def gestao():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado. Apenas Administradores.', 'danger')
        return redirect(url_for('estoque.index'))
    q = (request.args.get('q') or '').strip()
    view = (request.args.get('view') or '').strip()
    # QR removido
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols_meta = [c['name'] for c in insp.get_columns('collaborator')]
        changed = False
        if 'name' not in cols_meta:
            db.session.execute(text('ALTER TABLE collaborator ADD COLUMN name TEXT'))
            changed = True
            if 'nome' in cols_meta:
                try:
                    db.session.execute(text('UPDATE collaborator SET name = nome WHERE name IS NULL'))
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
        try:
            # leave_assignment: notes
            la_cols = [c['name'] for c in insp.get_columns('leave_assignment')]
            la_changed = False
            if 'notes' not in la_cols:
                db.session.execute(text('ALTER TABLE leave_assignment ADD COLUMN notes TEXT'))
                la_changed = True
            if la_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            # leave_credit: origin, notes
            lc_cols = [c['name'] for c in insp.get_columns('leave_credit')]
            lc_changed = False
            if 'origin' not in lc_cols:
                db.session.execute(text('ALTER TABLE leave_credit ADD COLUMN origin TEXT'))
                lc_changed = True
            if 'notes' not in lc_cols:
                db.session.execute(text('ALTER TABLE leave_credit ADD COLUMN notes TEXT'))
                lc_changed = True
            if lc_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            # hour_bank_entry: reason
            hb_cols = [c['name'] for c in insp.get_columns('hour_bank_entry')]
            hb_changed = False
            if 'reason' not in hb_cols:
                db.session.execute(text('ALTER TABLE hour_bank_entry ADD COLUMN reason TEXT'))
                hb_changed = True
            if hb_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            # vacation: observacao
            vac_cols = [c['name'] for c in insp.get_columns('vacation')]
            vac_changed = False
            if 'observacao' not in vac_cols:
                db.session.execute(text('ALTER TABLE vacation ADD COLUMN observacao TEXT'))
                vac_changed = True
            if vac_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            # medical_certificate: motivo, cid, medico, foto_atestado
            mc_cols = [c['name'] for c in insp.get_columns('medical_certificate')]
            mc_changed = False
            if 'motivo' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN motivo TEXT'))
                mc_changed = True
            if 'cid' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN cid TEXT'))
                mc_changed = True
            if 'medico' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN medico TEXT'))
                mc_changed = True
            if 'foto_atestado' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN foto_atestado TEXT'))
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
        u_page = int(request.args.get('u_page', '1'))
    except Exception:
        u_page = 1
    try:
        l_page = int(request.args.get('l_page', '1'))
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
        logs.append({'data': h.data, 'origem': 'Estoque', 'evento': h.action, 'detalhes': h.details, 'usuario': h.usuario, 'produto': h.product_name, 'quantidade': h.quantidade})
    for h in hist_limpeza:
        logs.append({'data': h.data_conclusao, 'origem': 'Limpeza', 'evento': 'conclusao', 'detalhes': h.observacao, 'usuario': h.usuario_conclusao, 'produto': h.nome_limpeza, 'quantidade': None})
    for s in hist_sistema:
        logs.append({'data': s.data, 'origem': s.origem, 'evento': s.evento, 'detalhes': s.detalhes, 'usuario': s.usuario, 'produto': None, 'quantidade': None})
    logs.sort(key=lambda x: x['data'], reverse=True)
    # Busca e paginação de usuários
    uq = User.query
    if q:
        uq = uq.filter(User.name.ilike(f"%{q}%"))
    all_users: list[User] = uq.order_by(User.username.asc()).all()
    per_users = 5
    total_users = len(all_users)
    u_total_pages = max(1, (total_users + per_users - 1) // per_users)
    if u_page > u_total_pages:
        u_page = u_total_pages
    u_start = (u_page - 1) * per_users
    u_end = u_start + per_users
    users_page = all_users[u_start:u_end]

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
        acc_user = (request.args.get('acc_user') or '').strip()
    except Exception:
        acc_user = ''
    try:
        acc_page = int(request.args.get('acc_page', '1'))
    except Exception:
        acc_page = 1
    if acc_page < 1:
        acc_page = 1
    aq = SystemLog.query.filter(SystemLog.origem == 'Acesso', SystemLog.evento == 'login')
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

    senha_sugestao = '123456'
    roles = JobRole.query.order_by(JobRole.name.asc()).all()
    colaboradores = Collaborator.query.order_by(Collaborator.name.asc()).all()
    bank_balances = {}
    saldo_collab = None
    saldo_hours = None
    saldo_days = None
    saldo_items = []
    saldo_start = None
    saldo_end = None
    try:
        from sqlalchemy import func
        sums = db.session.query(HourBankEntry.collaborator_id, func.coalesce(func.sum(HourBankEntry.hours), 0.0)).group_by(HourBankEntry.collaborator_id).all()
        for cid, total in sums:
            bank_balances[int(cid)] = float(total or 0.0)
        try:
            scid = request.args.get('saldo_collaborator_id', type=int)
        except Exception:
            scid = None
        try:
            raw_start = request.args.get('saldo_start', '') or ''
            raw_end = request.args.get('saldo_end', '') or ''
            from datetime import datetime as _dt2
            if isinstance(raw_start, str) and raw_start.strip():
                saldo_start = _dt2.strptime(raw_start.strip(), '%Y-%m-%d').date()
            else:
                saldo_start = None
            if isinstance(raw_end, str) and raw_end.strip():
                saldo_end = _dt2.strptime(raw_end.strip(), '%Y-%m-%d').date()
            else:
                saldo_end = None
        except Exception:
            saldo_start = None
            saldo_end = None
        if scid:
            saldo_collab = Collaborator.query.get(scid)
            if saldo_collab:
                try:
                    hsum_pre = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == scid).scalar() or 0.0
                    hsum_pre = float(hsum_pre)
                    auto_pre = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == scid, LeaveCredit.origin == 'horas').scalar() or 0
                    auto_pre = int(auto_pre)
                    desired_pre = int(hsum_pre // 8.0) if hsum_pre > 0.0 else 0
                    missing_pre = max(0, desired_pre - auto_pre)
                    if missing_pre > 0:
                        from datetime import date as _date
                        for _ in range(missing_pre):
                            lc = LeaveCredit()
                            lc.collaborator_id = scid
                            lc.date = _date.today()
                            lc.amount_days = 1
                            lc.origin = 'horas'
                            lc.notes = 'Reconciliação automática: crédito por 8h acumuladas'
                            db.session.add(lc)
                        for _ in range(missing_pre):
                            adj = HourBankEntry()
                            adj.collaborator_id = scid
                            adj.date = _date.today()
                            adj.hours = -8.0
                            adj.reason = 'Reconciliação automática: -8h por +1 dia'
                            db.session.add(adj)
                        db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                hsum = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == scid).scalar() or 0.0
                hsum = float(hsum)
                if hsum >= 0.0:
                    saldo_hours = hsum % 8.0
                else:
                    saldo_hours = - ((-hsum) % 8.0)
                credits_sum = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == scid).scalar() or 0
                assigned_sum = db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == scid).scalar() or 0
                converted_sum = db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == scid).scalar() or 0
                saldo_days = int(credits_sum) - int(assigned_sum) - int(converted_sum)
                try:
                    # Detalhamento por período
                    hq = HourBankEntry.query.filter(HourBankEntry.collaborator_id == scid)
                    cq = LeaveCredit.query.filter(LeaveCredit.collaborator_id == scid)
                    aq = LeaveAssignment.query.filter(LeaveAssignment.collaborator_id == scid)
                    if saldo_start and saldo_end:
                        hq = hq.filter(HourBankEntry.date.between(saldo_start, saldo_end))
                        cq = cq.filter(LeaveCredit.date.between(saldo_start, saldo_end))
                        aq = aq.filter(LeaveAssignment.date.between(saldo_start, saldo_end))
                    elif saldo_start:
                        hq = hq.filter(HourBankEntry.date >= saldo_start)
                        cq = cq.filter(LeaveCredit.date >= saldo_start)
                        aq = aq.filter(LeaveAssignment.date >= saldo_start)
                    elif saldo_end:
                        hq = hq.filter(HourBankEntry.date <= saldo_end)
                        cq = cq.filter(LeaveCredit.date <= saldo_end)
                        aq = aq.filter(LeaveAssignment.date <= saldo_end)
                    h_list = hq.order_by(HourBankEntry.date.desc()).all()
                    c_list = cq.order_by(LeaveCredit.date.desc()).all()
                    a_list = aq.order_by(LeaveAssignment.date.desc()).all()
                    # Unificar itens
                    for e in h_list:
                        saldo_items.append({
                            'tipo': 'horas',
                            'date': e.date,
                            'amount': float(e.hours or 0.0),
                            'unit': 'h',
                            'motivo': e.reason or ''
                        })
                    for c in c_list:
                        saldo_items.append({
                            'tipo': 'credito',
                            'date': c.date,
                            'amount': int(c.amount_days or 0),
                            'unit': 'dia',
                            'motivo': (c.origin or 'manual')
                                + ((' — ' + (c.notes or '')) if c.notes else '')
                        })
                    for a in a_list:
                        saldo_items.append({
                            'tipo': 'uso',
                            'date': a.date,
                            'amount': -int(a.days_used or 0),
                            'unit': 'dia',
                            'motivo': a.notes or ''
                        })
                    saldo_items.sort(key=lambda x: x['date'], reverse=True)
                except Exception:
                    saldo_items = []
    except Exception:
        bank_balances = {}
    recent_entries = []
    try:
        recent_entries = HourBankEntry.query.order_by(HourBankEntry.date.desc()).limit(50).all()
    except Exception:
        recent_entries = []
    folgas = []
    try:
        from sqlalchemy import func
        for c in colaboradores:
            credits_sum = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == c.id).scalar() or 0
            assigned_sum = db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == c.id).scalar() or 0
            converted_sum = db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == c.id).scalar() or 0
            folgas.append({'collab': c, 'balance': int(credits_sum) - int(assigned_sum) - int(converted_sum)})
    except Exception:
        folgas = []
    # Paginação e filtros por colaborador
    per_page = 10
    # Banco de Horas (lista de colaboradores)
    try:
        bh_collab_id = request.args.get('bh_collaborator_id', type=int)
    except Exception:
        bh_collab_id = None
    try:
        bh_page = int(request.args.get('bh_page', '1'))
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
        lc_collab_id = request.args.get('lc_collaborator_id', type=int)
    except Exception:
        lc_collab_id = None
    try:
        lc_page = int(request.args.get('lc_page', '1'))
    except Exception:
        lc_page = 1
    if lc_page < 1:
        lc_page = 1
    lc_q = LeaveCredit.query.order_by(LeaveCredit.date.desc())
    if lc_collab_id:
        lc_q = lc_q.filter(LeaveCredit.collaborator_id == lc_collab_id)
    leave_credits_all = lc_q.all()
    lc_total_pages = max(1, (len(leave_credits_all) + per_page - 1) // per_page)
    if lc_page > lc_total_pages:
        lc_page = lc_total_pages
    lc_start = (lc_page - 1) * per_page
    lc_end = lc_start + per_page
    leave_credits_page = leave_credits_all[lc_start:lc_end]
    # Uso de Folgas
    try:
        la_collab_id = request.args.get('la_collaborator_id', type=int)
    except Exception:
        la_collab_id = None
    try:
        la_page = int(request.args.get('la_page', '1'))
    except Exception:
        la_page = 1
    if la_page < 1:
        la_page = 1
    la_q = LeaveAssignment.query.order_by(LeaveAssignment.date.desc())
    if la_collab_id:
        la_q = la_q.filter(LeaveAssignment.collaborator_id == la_collab_id)
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
            with open('/proc/uptime', 'r') as f:
                secs = float((f.read().split()[0] or '0').strip())
            days = int(secs // 86400)
            rem = secs % 86400
            hours = int(rem // 3600)
            minutes = int((rem % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"
        except Exception:
            try:
                out = subprocess.check_output(['uptime', '-p'], timeout=2)
                uptime_str = (out.decode('utf-8', errors='ignore') or '').strip()
            except Exception:
                uptime_str = None
        load_str = None
        try:
            import os as _os
            la_fn = getattr(_os, 'getloadavg', None)
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
                    with open('/proc/loadavg', 'r') as f:
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
            units = ['B','KB','MB','GB','TB','PB']
            f = float(n)
            for u in units:
                if f < 1024.0:
                    return f"{f:.1f} {u}"
                f = f / 1024.0
            return f"{f:.1f} EB"
        vps_storage = {
            'total': du.total,
            'used': du.used,
            'free': du.free,
            'total_str': _fmt_bytes(du.total),
            'used_str': _fmt_bytes(du.used),
            'free_str': _fmt_bytes(du.free),
            'used_pct': int((du.used / du.total) * 100) if du.total > 0 else 0
            , 'uptime_str': uptime_str
            , 'load_str': load_str
        }
    except Exception:
        vps_storage = None
    # Removido endereço de acesso (url/qr), mantendo somente dados necessários
    # Férias
    try:
        ferias_collab_id = request.args.get('ferias_collaborator_id', type=int)
    except Exception:
        ferias_collab_id = None
    try:
        ferias_page = int(request.args.get('ferias_page', '1'))
    except Exception:
        ferias_page = 1
    if ferias_page < 1:
        ferias_page = 1
    ferias_q = Vacation.query.order_by(Vacation.data_inicio.desc())
    if ferias_collab_id:
        ferias_q = ferias_q.filter(Vacation.collaborator_id == ferias_collab_id)
    ferias_all = ferias_q.all()
    ferias_total_pages = max(1, (len(ferias_all) + per_page - 1) // per_page)
    if ferias_page > ferias_total_pages:
        ferias_page = ferias_total_pages
    ferias_start = (ferias_page - 1) * per_page
    ferias_end = ferias_start + per_page
    ferias_page_items = ferias_all[ferias_start:ferias_end]
    # Atestados
    try:
        at_collab_id = request.args.get('at_collaborator_id', type=int)
    except Exception:
        at_collab_id = None
    try:
        at_page = int(request.args.get('at_page', '1'))
    except Exception:
        at_page = 1
    if at_page < 1:
        at_page = 1
    at_q = MedicalCertificate.query.order_by(MedicalCertificate.data_inicio.desc())
    if at_collab_id:
        at_q = at_q.filter(MedicalCertificate.collaborator_id == at_collab_id)
    atestados_all = at_q.all()
    at_total_pages = max(1, (len(atestados_all) + per_page - 1) // per_page)
    if at_page > at_total_pages:
        at_page = at_total_pages
    at_start = (at_page - 1) * per_page
    at_end = at_start + per_page
    atestados_page = atestados_all[at_start:at_end]
    
    return render_template(
        'gestao.html',
        active_page='gestao',
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
        acc_user=acc_user
        , saldo_collab=saldo_collab, saldo_hours=saldo_hours, saldo_days=saldo_days, saldo_items=saldo_items, saldo_start=saldo_start, saldo_end=saldo_end
        , vps_storage=vps_storage
        , colaboradores_page=colaboradores_page, bh_page=bh_page, bh_total_pages=bh_total_pages, bh_collab_id=bh_collab_id
        , leave_credits_page=leave_credits_page, lc_page=lc_page, lc_total_pages=lc_total_pages, lc_collab_id=lc_collab_id
        , leave_assignments_page=leave_assignments_page, la_page=la_page, la_total_pages=la_total_pages, la_collab_id=la_collab_id
        , ferias_page_items=ferias_page_items, ferias_page=ferias_page, ferias_total_pages=ferias_total_pages, ferias_collab_id=ferias_collab_id
        , atestados_page=atestados_page, at_page=at_page, at_total_pages=at_total_pages, at_collab_id=at_collab_id
    )


@bp.route('/gestao/colaboradores/criar', methods=['POST'])
@login_required
def gestao_colabs_criar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para criar colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    nome = request.form.get('name', '').strip()
    cargo = request.form.get('role', '').strip()
    try:
        c = Collaborator()
        c.name = nome
        c.role = cargo
        c.active = True
        c.regular_team = (request.form.get('regular_team', '').strip() or None)
        c.sunday_team = (request.form.get('sunday_team', '').strip() or None)
        c.special_team = (request.form.get('special_team', '').strip() or None)
        uid_str = (request.form.get('user_id') or '').strip()
        try:
            c.user_id = int(uid_str) if uid_str else None
        except Exception:
            c.user_id = None
        db.session.add(c)
        db.session.commit()
        flash(f'Colaborador "{c.name}" criado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/colaboradores/<int:id>/editar', methods=['POST'])
@login_required
def gestao_colabs_editar(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para editar colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    c = Collaborator.query.get_or_404(id)
    try:
        c.name = ((request.form.get('name') or c.name or '').strip()) or c.name
        role_in = request.form.get('role')
        c.role = ((role_in or c.role or '').strip()) or None
        active_str = request.form.get('active', 'on') or 'on'
        c.active = True if active_str.lower() in ('on', 'true', '1') else False
        rt_in = request.form.get('regular_team') or (c.regular_team or '')
        st_in = request.form.get('sunday_team') or (c.sunday_team or '')
        xt_in = request.form.get('special_team') or (c.special_team or '')
        c.regular_team = (rt_in.strip() or None) if (rt_in.strip() in ('1','2')) else None
        c.sunday_team = (st_in.strip() or None) if (st_in.strip() in ('1','2')) else None
        c.special_team = (xt_in.strip() or None) if (xt_in.strip() in ('1','2')) else None
        uid_str = (request.form.get('user_id') or '').strip()
        try:
            c.user_id = int(uid_str) if uid_str else None
        except Exception:
            c.user_id = None
        db.session.commit()
        flash('Colaborador atualizado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/colaboradores/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_colabs_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode excluir colaboradores.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    c = Collaborator.query.get_or_404(id)
    try:
        Shift.query.filter_by(collaborator_id=c.id).delete()
        db.session.delete(c)
        db.session.commit()
        flash('Colaborador excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir colaborador: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/usuarios/associar', methods=['POST'])
@login_required
def gestao_usuarios_associar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para associar usuário a colaborador.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        uid = int(request.form.get('user_id', '0'))
    except Exception:
        uid = 0
    try:
        cid = int(request.form.get('collaborator_id', '0'))
    except Exception:
        cid = 0
    if uid <= 0:
        flash('Usuário inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        # Limpa associações anteriores para este usuário
        try:
            Collaborator.query.filter(Collaborator.user_id == uid).update({'user_id': None})
        except Exception:
            pass
        if cid > 0:
            c = Collaborator.query.get(cid)
            if not c:
                flash('Colaborador não encontrado.', 'warning')
                return redirect(url_for('usuarios.gestao'))
            c.user_id = uid
            db.session.add(c)
        db.session.commit()
        flash('Associação atualizada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao associar: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))
@bp.route('/gestao/colaboradores/horas/adicionar', methods=['POST'])
@login_required
def gestao_colabs_horas_adicionar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para registrar horas.', 'danger')
        return redirect(url_for('usuarios.gestao', view='colaboradores'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    hours_str = (request.form.get('hours', '0').strip() or '0')
    reason = (request.form.get('reason', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        h = float(hours_str)
    except Exception:
        flash('Dados inválidos para banco de horas.', 'warning')
        return redirect(url_for('usuarios.gestao', view='colaboradores'))
    try:
        e = HourBankEntry()
        e.collaborator_id = cid
        e.date = d
        e.hours = h
        e.reason = reason
        db.session.add(e)
        db.session.commit()
        try:
            from sqlalchemy import func
            total_hours = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == cid).scalar() or 0.0
            total_hours = float(total_hours)
            auto_credits = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == cid, LeaveCredit.origin == 'horas').scalar() or 0
            auto_credits = int(auto_credits)
            desired_credits = int(total_hours // 8.0)
            missing = max(0, desired_credits - auto_credits)
            if missing > 0:
                from datetime import date as _date
                for _ in range(missing):
                    lc = LeaveCredit()
                    lc.collaborator_id = cid
                    lc.date = _date.today()
                    lc.amount_days = 1
                    lc.origin = 'horas'
                    lc.notes = 'Crédito automático por 8h no banco de horas'
                    db.session.add(lc)
                for _ in range(missing):
                    adj = HourBankEntry()
                    adj.collaborator_id = cid
                    adj.date = _date.today()
                    adj.hours = -8.0
                    adj.reason = 'Conversão automática: -8h por +1 dia de folga'
                    db.session.add(adj)
                db.session.commit()
                flash(f'Horas registradas. Conversão automática aplicada: +{missing} dia(s) e -{missing*8}h no banco.', 'success')
            else:
                flash('Horas registradas.', 'success')
        except Exception as ex:
            flash('Horas registradas.', 'success')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao registrar horas: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='colaboradores'))

@bp.route('/gestao/colaboradores/horas/excluir/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_horas_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode excluir lançamentos.', 'danger')
        return redirect(url_for('usuarios.gestao', view='colaboradores'))
    e = HourBankEntry.query.get_or_404(id)
    try:
        cid = int(e.collaborator_id or 0)
        db.session.delete(e)
        db.session.commit()
        try:
            from sqlalchemy import func
            total_hours = db.session.query(func.coalesce(func.sum(HourBankEntry.hours), 0.0)).filter(HourBankEntry.collaborator_id == cid).scalar() or 0.0
            total_hours = float(total_hours)
            auto_credits = db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == cid, LeaveCredit.origin == 'horas').scalar() or 0
            auto_credits = int(auto_credits)
            desired_credits = int(total_hours // 8.0)
            if auto_credits > desired_credits:
                excess = auto_credits - desired_credits
                to_delete_credits = LeaveCredit.query.filter_by(collaborator_id=cid, origin='horas').order_by(LeaveCredit.date.desc(), LeaveCredit.id.desc()).limit(excess).all()
                for lc in to_delete_credits:
                    db.session.delete(lc)
                to_delete_adjusts = (
                    HourBankEntry.query
                    .filter(HourBankEntry.collaborator_id == cid, HourBankEntry.hours == -8.0, HourBankEntry.reason.like('Conversão automática:%'))
                    .order_by(HourBankEntry.date.desc(), HourBankEntry.id.desc())
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
                        comp = HourBankEntry()
                        comp.collaborator_id = cid
                        comp.date = _date.today()
                        comp.hours = +8.0
                        comp.reason = 'Reversão automática: +8h pela exclusão de crédito por horas'
                        db.session.add(comp)
                    db.session.commit()
                flash(f'Lançamento excluído. Conversões automáticas revertidas: -{excess} dia(s) e +{excess*8}h no banco.', 'warning')
            elif auto_credits < desired_credits:
                missing = desired_credits - auto_credits
                from datetime import date as _date
                for _ in range(missing):
                    lc = LeaveCredit()
                    lc.collaborator_id = cid
                    lc.date = _date.today()
                    lc.amount_days = 1
                    lc.origin = 'horas'
                    lc.notes = 'Crédito automático por 8h no banco de horas (ajuste pós-exclusão)'
                    db.session.add(lc)
                for _ in range(missing):
                    adj = HourBankEntry()
                    adj.collaborator_id = cid
                    adj.date = _date.today()
                    adj.hours = -8.0
                    adj.reason = 'Conversão automática: -8h por +1 dia de folga (ajuste pós-exclusão)'
                    db.session.add(adj)
                db.session.commit()
                flash(f'Lançamento excluído. Conversões automáticas ajustadas: +{missing} dia(s) e -{missing*8}h no banco.', 'info')
            else:
                flash('Lançamento excluído.', 'success')
        except Exception as ex:
            flash('Lançamento excluído.', 'success')
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f'Erro ao excluir lançamento: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='colaboradores'))

@bp.route('/gestao/colaboradores/horas/editar/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_horas_editar(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode editar lançamentos.', 'danger')
        return redirect(url_for('usuarios.gestao', view='colaboradores'))
    e = HourBankEntry.query.get_or_404(id)
    date_str = (request.form.get('date', '').strip() or '')
    hours_str = (request.form.get('hours', '0').strip() or '0')
    reason = (request.form.get('reason', '').strip() or '')
    try:
        if date_str:
            e.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        e.hours = float(hours_str)
        e.reason = reason
        db.session.commit()
        flash('Lançamento de horas atualizado.', 'info')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao editar lançamento: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='colaboradores'))

@bp.route('/gestao/colaboradores/folgas/credito/adicionar', methods=['POST'])
@login_required
def gestao_colabs_folga_credito_adicionar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para registrar folgas.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('amount_days', '1').strip() or '1')
    origin = (request.form.get('origin', 'manual').strip() or 'manual')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        days = int(days_str)
    except Exception:
        flash('Dados inválidos para crédito de folga.', 'warning')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    try:
        lc = LeaveCredit()
        lc.collaborator_id = cid
        lc.date = d
        lc.amount_days = days
        lc.origin = origin
        lc.notes = notes
        db.session.add(lc)
        db.session.commit()
        flash(f'Crédito de {days} dia(s) de folga registrado.', 'success')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao registrar crédito: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/colaboradores/folgas/credito/editar/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_folga_credito_editar(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode editar créditos de folga.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    lc = LeaveCredit.query.get_or_404(id)
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('amount_days', '').strip() or '')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        if date_str:
            lc.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if days_str:
            lc.amount_days = int(days_str)
        lc.notes = notes
        db.session.commit()
        flash('Crédito de folga atualizado.', 'info')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao editar crédito: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/colaboradores/folgas/credito/excluir/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_folga_credito_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode excluir créditos de folga.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    lc = LeaveCredit.query.get_or_404(id)
    try:
        db.session.delete(lc)
        db.session.commit()
        flash('Crédito de folga excluído.', 'danger')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao excluir crédito: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/colaboradores/folgas/uso/adicionar', methods=['POST'])
@login_required
def gestao_colabs_folga_uso_adicionar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Você não tem permissão para registrar uso de folgas.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    cid_str = (request.form.get('collaborator_id', '').strip() or '')
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('days_used', '1').strip() or '1')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        from datetime import timedelta
        cid = int(cid_str)
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        days = int(days_str)
    except Exception:
        flash('Dados inválidos para uso de folga.', 'warning')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    try:
        try:
            end_d = d + timedelta(days=max(1, days) - 1)
            feriados_no_periodo = Holiday.query.filter(Holiday.date >= d, Holiday.date <= end_d).count()
        except Exception:
            feriados_no_periodo = 0
        effective_days = max(0, int(days) - int(feriados_no_periodo))

        from sqlalchemy import func
        credits_sum = int(db.session.query(func.coalesce(func.sum(LeaveCredit.amount_days), 0)).filter(LeaveCredit.collaborator_id == cid).scalar() or 0)
        assigned_sum = int(db.session.query(func.coalesce(func.sum(LeaveAssignment.days_used), 0)).filter(LeaveAssignment.collaborator_id == cid).scalar() or 0)
        converted_sum = int(db.session.query(func.coalesce(func.sum(LeaveConversion.amount_days), 0)).filter(LeaveConversion.collaborator_id == cid).scalar() or 0)
        saldo_days = credits_sum - assigned_sum - converted_sum

        if effective_days < 1 or effective_days > saldo_days:
            flash('Saldo insuficiente de folgas.', 'warning')
            return redirect(url_for('usuarios.gestao', view='folgas'))

        la = LeaveAssignment()
        la.collaborator_id = cid
        la.date = d
        la.days_used = effective_days
        la.notes = notes
        db.session.add(la)
        db.session.commit()
        flash(f'Uso de {effective_days} dia(s) de folga registrado.', 'success')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao registrar uso: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/colaboradores/folgas/uso/editar/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_folga_uso_editar(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode editar uso de folga.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    la = LeaveAssignment.query.get_or_404(id)
    date_str = (request.form.get('date', '').strip() or '')
    days_str = (request.form.get('days_used', '').strip() or '')
    notes = (request.form.get('notes', '').strip() or '')
    try:
        from datetime import timedelta
        if date_str:
            la.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # recalcular dias efetivos desconsiderando feriados
        if days_str:
            try:
                new_days = int(days_str)
                end_d = la.date + timedelta(days=max(1, new_days) - 1)
                feriados_no_periodo = Holiday.query.filter(Holiday.date >= la.date, Holiday.date <= end_d).count()
            except Exception:
                feriados_no_periodo = 0
            la.days_used = max(0, int(new_days) - int(feriados_no_periodo))
        la.notes = notes
        db.session.commit()
        flash('Uso de folga atualizado.', 'info')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao editar uso: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/colaboradores/folgas/uso/excluir/<int:id>', methods=['POST'])
@login_required
def gestao_colabs_folga_uso_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Apenas Gerente pode excluir uso de folga.', 'danger')
        return redirect(url_for('usuarios.gestao', view='folgas'))
    la = LeaveAssignment.query.get_or_404(id)
    try:
        db.session.delete(la)
        db.session.commit()
        flash('Uso de folga excluído.', 'danger')
    except Exception as ex:
        db.session.rollback()
        flash(f'Erro ao excluir uso: {ex}', 'danger')
    return redirect(url_for('usuarios.gestao', view='folgas'))

@bp.route('/gestao/roles', methods=['POST'])
@login_required
def gestao_role_criar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    name = (request.form.get('name') or '').strip()
    nivel = (request.form.get('nivel') or 'visualizador').strip()
    if not name:
        flash('Nome do cargo é obrigatório.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    if nivel not in ('visualizador','operador','admin'):
        flash('Tipo de permissão inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    if JobRole.query.filter_by(name=name).first() is not None:
        flash('Cargo já existe.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        r = JobRole()
        r.name = name
        r.nivel = nivel
        db.session.add(r)
        db.session.commit()
        flash('Cargo criado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/roles/<int:id>/editar', methods=['POST'])
@login_required
def gestao_role_editar(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    role = JobRole.query.get_or_404(id)
    name = (request.form.get('name') or role.name).strip()
    nivel = (request.form.get('nivel') or role.nivel).strip()
    if nivel not in ('visualizador','operador','admin'):
        flash('Tipo de permissão inválido.', 'warning')
        return redirect(url_for('usuarios.gestao'))
    try:
        role.name = name
        role.nivel = nivel
        db.session.commit()
        flash('Cargo atualizado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))

@bp.route('/gestao/roles/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_role_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    role = JobRole.query.get_or_404(id)
    try:
        db.session.delete(role)
        db.session.commit()
        flash('Cargo excluído.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir cargo: {e}', 'danger')
    return redirect(url_for('usuarios.gestao'))


@bp.route('/gestao/ferias/adicionar', methods=['POST'])
@login_required
def gestao_ferias_adicionar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('usuarios.gestao') + '#ferias')
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        observacao = request.form.get('observacao', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('usuarios.gestao') + '#ferias')
        
        v = Vacation()
        v.collaborator_id = cid
        v.data_inicio = data_inicio
        v.data_fim = data_fim
        v.observacao = observacao
        v.criado_por = current_user.name
        db.session.add(v)
        db.session.commit()
        flash('Férias registradas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar férias: {e}', 'danger')
    return redirect(url_for('usuarios.gestao') + '#ferias')


@bp.route('/gestao/ferias/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_ferias_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    v = Vacation.query.get_or_404(id)
    try:
        db.session.delete(v)
        db.session.commit()
        flash('Férias excluídas.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('usuarios.gestao') + '#ferias')


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@bp.route('/gestao/atestado/adicionar', methods=['POST'])
@login_required
def gestao_atestado_adicionar():
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    try:
        import os
        
        cid_str = (request.form.get('collaborator_id') or '').strip()
        di_str = (request.form.get('data_inicio') or '').strip()
        df_str = (request.form.get('data_fim') or '').strip()
        if not cid_str or not di_str or not df_str:
            flash('Dados obrigatórios ausentes.', 'warning')
            return redirect(url_for('usuarios.gestao') + '#atestados')
        cid = int(cid_str)
        data_inicio = datetime.strptime(di_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(df_str, '%Y-%m-%d').date()
        motivo = request.form.get('motivo', '').strip()
        cid_code = request.form.get('cid', '').strip()
        medico = request.form.get('medico', '').strip()
        
        if data_fim < data_inicio:
            flash('Data final deve ser maior ou igual à data inicial.', 'warning')
            return redirect(url_for('usuarios.gestao') + '#atestados')
        
        dias = (data_fim - data_inicio).days + 1
        
        foto_filename = None
        if 'foto_atestado' in request.files:
            foto = request.files['foto_atestado']
            if foto and foto.filename:
                if not allowed_file(foto.filename):
                    flash('Tipo de arquivo não permitido. Use imagens (PNG, JPG, JPEG, GIF).', 'warning')
                    return redirect(url_for('usuarios.gestao') + '#atestados')
                
                foto.seek(0, 2)
                size = foto.tell()
                foto.seek(0)
                if size > MAX_UPLOAD_SIZE:
                    flash('Arquivo muito grande. Máximo 10MB.', 'warning')
                    return redirect(url_for('usuarios.gestao') + '#atestados')
                
                upload_dir = os.path.join('static', 'uploads', 'atestados')
                os.makedirs(upload_dir, exist_ok=True)
                safe_name = secure_filename(foto.filename)
                ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
                foto_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cid}.{ext}"
                foto.save(os.path.join(upload_dir, foto_filename))
        
        m = MedicalCertificate()
        m.collaborator_id = cid
        m.data_inicio = data_inicio
        m.data_fim = data_fim
        m.dias = dias
        m.motivo = motivo
        m.cid = cid_code
        m.medico = medico
        m.foto_atestado = foto_filename
        m.criado_por = current_user.name
        db.session.add(m)
        db.session.commit()
        flash('Atestado registrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar atestado: {e}', 'danger')
    return redirect(url_for('usuarios.gestao') + '#atestados')


@bp.route('/gestao/atestado/<int:id>/excluir', methods=['POST'])
@login_required
def gestao_atestado_excluir(id: int):
    if current_user.nivel not in ('admin', 'DEV'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('usuarios.gestao'))
    m = MedicalCertificate.query.get_or_404(id)
    try:
        if m.foto_atestado:
            import os
            path = os.path.join('static', 'uploads', 'atestados', m.foto_atestado)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(m)
        db.session.commit()
        flash('Atestado excluído.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('usuarios.gestao') + '#atestados')
