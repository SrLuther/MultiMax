from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import Collaborator as CollaboratorModel
from ..models import Holiday, MedicalCertificate, TimeOffRecord
from ..models import Vacation as VacationModel
from ..services.notificacao_service import registrar_evento

bp = Blueprint("colaboradores", __name__)


def _ensure_collaborator_name_column():
    """Garante que a coluna 'name' existe na tabela 'collaborator'."""
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
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _get_week_dates(semana_param, today):
    """Calcula as datas do início e fim da semana."""
    from datetime import timedelta

    try:
        if semana_param:
            semana_inicio = datetime.strptime(semana_param, "%Y-%m-%d").date()
        else:
            semana_inicio = today
        semana_inicio = semana_inicio - timedelta(days=semana_inicio.weekday())
    except Exception:
        semana_inicio = today - timedelta(days=today.weekday())

    semana_fim = semana_inicio + timedelta(days=6)
    return semana_inicio, semana_fim


def _check_folga_status(colab_id, dia_data):
    """Verifica se há folga registrada para a data."""
    from datetime import timedelta

    try:
        folgas = (
            TimeOffRecord.query.filter(
                TimeOffRecord.collaborator_id == colab_id,
                TimeOffRecord.record_type == "folga_usada",
                TimeOffRecord.date <= dia_data,
            )
            .order_by(TimeOffRecord.date.desc())
            .limit(5)
            .all()
        )
        for folga in folgas:
            days = max(1, int(folga.days or 1))
            end_date = folga.date + timedelta(days=days - 1)
            if folga.date <= dia_data <= end_date:
                return "Folga"
    except Exception:
        pass
    return None


def _check_vacation_status(colab_id, dia_data):
    """Verifica se há férias registradas para a data."""
    try:
        vac = VacationModel.query.filter(
            VacationModel.collaborator_id == colab_id,
            VacationModel.data_inicio <= dia_data,
            VacationModel.data_fim >= dia_data,
        ).first()
        return "Férias" if vac else None
    except Exception:
        return None


def _check_medical_status(colab_id, dia_data):
    """Verifica se há atestado médico registrado para a data."""
    try:
        mc = MedicalCertificate.query.filter(
            MedicalCertificate.collaborator_id == colab_id,
            MedicalCertificate.data_inicio <= dia_data,
            MedicalCertificate.data_fim >= dia_data,
        ).first()
        return "Atestado" if mc else None
    except Exception:
        return None


def _build_status_map(cols, dias_semana):
    """Constrói mapa de status (Folga, Férias, Atestado) por colaborador/data."""
    status_map = {}

    for colab in cols:
        for dia in dias_semana:
            key = (colab.id, dia["data"].isoformat())

            # Verificar com prioridade: Atestado > Férias > Folga
            status = _check_medical_status(colab.id, dia["data"])
            if not status:
                status = _check_vacation_status(colab.id, dia["data"])
            if not status:
                status = _check_folga_status(colab.id, dia["data"])

            if status:
                status_map[key] = status

    return status_map


def _build_dias_semana(semana_inicio, today):
    dias_nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    dias_semana = []
    for i in range(7):
        d = semana_inicio + timedelta(days=i)
        dias_semana.append({"data": d, "nome": dias_nomes[i], "is_today": d == today})
    return dias_semana


def _calculate_semana_context(semana_param, today):
    semana_inicio, semana_fim = _get_week_dates(semana_param, today)
    semana_anterior = (semana_inicio - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_proxima = (semana_inicio + timedelta(days=7)).strftime("%Y-%m-%d")
    dias_semana = _build_dias_semana(semana_inicio, today)
    return semana_inicio, semana_fim, semana_anterior, semana_proxima, dias_semana


@bp.route("/gestao/folga/credito", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_registrar_gestao():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para registrar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para crédito de folga.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        lc = TimeOffRecord()
        lc.collaborator_id = cid
        lc.date = d
        lc.record_type = "folga_adicional"
        lc.days = amount
        lc.origin = "manual"
        lc.notes = notes
        lc.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(lc)
        db.session.commit()
        flash("Crédito de folga registrado.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar crédito: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/credito/domingo", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_domingo():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para registrar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or "Domingo trabalhado"
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para crédito de domingo.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        exists = TimeOffRecord.query.filter(
            TimeOffRecord.collaborator_id == cid,
            TimeOffRecord.date == d,
            TimeOffRecord.record_type == "folga_adicional",
            TimeOffRecord.origin == "domingo",
        ).first()
        if not exists:
            lc = TimeOffRecord()
            lc.collaborator_id = cid
            lc.date = d
            lc.record_type = "folga_adicional"
            lc.days = amount
            lc.origin = "domingo"
            lc.notes = notes
            lc.created_by = current_user.username if current_user.is_authenticated else "sistema"
            db.session.add(lc)
            db.session.commit()
            flash("Crédito de domingo registrado.", "success")
        else:
            flash("Crédito de domingo já existe para essa data.", "info")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar crédito: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/credito/reduzir", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_reduzir():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para ajustar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or "Ajuste negativo"
    try:
        cid = int(cid_str)
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para ajuste.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        from datetime import date as _date

        lc = TimeOffRecord()
        lc.collaborator_id = cid
        lc.date = _date.today()
        lc.record_type = "folga_adicional"
        lc.days = -amount
        lc.origin = "ajuste"
        lc.notes = notes
        db.session.add(lc)
        db.session.commit()
        flash("Ajuste aplicado: dias reduzidos.", "warning")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao ajustar créditos: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/agendar", methods=["POST"], strict_slashes=False)
@login_required
def folga_agendar():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para agendar folga.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = max(1, int(days_str))
    except Exception:
        flash("Dados inválidos para agendamento.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        from sqlalchemy import func

        credits_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_adicional")
            .scalar()
            or 0
        )
        assigned_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_usada")
            .scalar()
            or 0
        )
        converted_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "conversao")
            .scalar()
            or 0
        )
        folga_balance = int(credits_sum) - int(assigned_sum) - int(converted_sum)
        if folga_balance < days:
            flash(
                f"Saldo de folga insuficiente ({folga_balance} dia(s)). Reduza os dias ou converta em dinheiro.",
                "warning",
            )
            return redirect(url_for("usuarios.gestao") + "#folgas")
    except Exception:
        pass
    try:
        from datetime import timedelta

        try:
            end_d = d + timedelta(days=max(1, days) - 1)
            feriados_no_periodo = Holiday.query.filter(Holiday.date >= d, Holiday.date <= end_d).count()
        except Exception:
            feriados_no_periodo = 0
        effective_days = max(0, int(days) - int(feriados_no_periodo))
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
        try:
            col = CollaboratorModel.query.get(cid)
            nome = col.name if col and col.name else f"ID {cid}"
        except Exception:
            nome = f"ID {cid}"
        registrar_evento("folga cadastrada", produto=nome, quantidade=days, descricao=notes)
        flash("Folga agendada.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao agendar folga: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/converter", methods=["POST"], strict_slashes=False)
@login_required
def folga_converter():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para converter folga.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days", "1").strip() or "1"
    amount_str = request.form.get("amount_paid", "").strip() or ""
    rate_str = request.form.get("rate_per_day", "65").strip() or "65"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = max(1, int(days_str))
        rate = float(rate_str)
        amount_paid = float(amount_str) if amount_str else (rate * days)
    except Exception:
        flash("Dados inválidos para conversão.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        conv = TimeOffRecord()
        conv.collaborator_id = cid
        conv.date = d
        conv.record_type = "conversao"
        conv.days = days
        conv.amount_paid = amount_paid
        conv.rate_per_day = rate
        conv.notes = notes
        conv.origin = "manual"
        conv.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(conv)
        db.session.commit()
        flash("Conversão registrada.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar conversão: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))
