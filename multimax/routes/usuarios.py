import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Sequence, cast

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import (
    AppSetting,
    ArticleVote,
    Ciclo,
    CleaningHistory,
    CleaningTask,
    Collaborator,
    Historico,
    Holiday,
    JobRole,
    MeatReception,
    MedicalCertificate,
    NotificationRead,
    Produto,
    RegistroJornadaChange,
    Setor,
    Shift,
    SuggestionVote,
    SystemLog,
    TimeOffRecord,
    User,
    UserLogin,
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


def _safe_int_arg(name: str, default: int) -> int:
    try:
        raw = request.args.get(name, default)
        val = int(raw)
        return val if val > 0 else default
    except Exception:
        return default


def _paginate_list(items, page: int, per_page: int):
    per_page = per_page or 1
    try:
        page = int(page)
    except Exception:
        page = 1
    if page < 1:
        page = 1
    data = items or []
    total = len(data)
    total_pages = max(1, int((total + per_page - 1) // per_page))
    start = (page - 1) * per_page
    end = start + per_page
    page_items = data[start:end]
    return page_items, total_pages, min(page, total_pages)


def _handle_perfil_post():
    if current_user.nivel == "visualizador":
        return _update_viewer_profile()
    return _update_full_profile()


def _update_viewer_profile():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Nome é obrigatório.", "warning")
        return redirect(url_for("usuarios.perfil"))
    current_user.name = name
    return _commit_and_redirect("Perfil atualizado.")


def _update_full_profile():
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
    return _commit_and_redirect("Perfil atualizado.")


def _commit_and_redirect(success_message: str):
    try:
        db.session.commit()
        flash(success_message, "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar perfil: {e}", "danger")
    return redirect(url_for("usuarios.perfil"))


def _rollback_log_warning(error, context: str):
    try:
        db.session.rollback()
    except Exception:
        pass
    try:
        current_app.logger.warning(f"Erro durante {context}: {error}", exc_info=True)
    except Exception:
        pass


def _ensure_collaborator_user_column():
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


def _ensure_collaborator_schema():
    try:
        _ensure_collaborator_user_column()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _perfil_collaborator_payload():
    collab = None
    balance_data = None
    entries = []
    try:
        collab = Collaborator.query.filter_by(user_id=current_user.id).first()
        if collab:
            from ..routes.ciclos import _calculate_collaborator_balance

            balance = _calculate_collaborator_balance(collab.id)
            balance_data = {
                "total_horas": balance["total_horas"],
                "dias_completos": balance["dias_completos"],
                "horas_restantes": balance["horas_restantes"],
                "valor_aproximado": balance["valor_aproximado"],
            }
            entries = (
                Ciclo.query.filter(Ciclo.collaborator_id == collab.id, Ciclo.status_ciclo == "ativo")
                .order_by(Ciclo.data_lancamento.desc(), Ciclo.id.desc())
                .limit(50)
                .all()
            )
    except Exception:
        collab = None
        balance_data = None
        entries = []
    return collab, balance_data, entries


def _perfil_values(collab, balance_data):
    if not (collab and balance_data):
        return None, 0.0
    day_value = _perfil_day_value()
    collaborator_values = {
        "full_days": balance_data["dias_completos"],
        "residual_hours": balance_data["horas_restantes"],
        "day_value": day_value,
        "value_full_days": balance_data["valor_aproximado"],
        "value_residual_hours": 0.0,
        "value_total_individual": balance_data["valor_aproximado"],
    }
    return collaborator_values, day_value


def _perfil_day_value():
    try:
        setting = AppSetting.query.filter_by(key="ciclo_valor_dia").first()
        if setting and setting.value:
            return float(setting.value)
    except Exception:
        pass
    return 65.0


def _perfil_status_flags(collab):
    status = {
        "is_on_break": False,
        "is_on_vacation": False,
        "vacation_end_date": None,
        "vacation_end_timestamp": 0,
        "vacation_return_hour": "05:00",
        "is_on_medical": False,
        "medical_end_timestamp": 0,
        "medical_end_date": None,
        "break_end_timestamp": 0,
        "next_shift_date": None,
        "next_shift_hour": None,
    }
    if not collab:
        return status

    from datetime import date as _date

    today = _date.today()
    status.update(_perfil_break_status(collab, today))
    status.update(_perfil_next_shift_status(collab, today))
    status.update(_perfil_vacation_status(collab, today))
    status.update(_perfil_medical_status(collab, today))
    return status


def _perfil_break_status(collab, today):
    from datetime import datetime as _dt

    data = {"is_on_break": False, "break_end_timestamp": 0}
    try:
        today_shift = Shift.query.filter_by(collaborator_id=collab.id, date=today).first()
        if today_shift and (
            (today_shift.shift_type or "").lower() == "folga" or (today_shift.turno or "").lower() == "folga"
        ):
            end_dt = _dt.combine(today, _dt.min.time().replace(hour=23, minute=59, second=59))
            data["is_on_break"] = True
            data["break_end_timestamp"] = int(end_dt.timestamp())
    except Exception:
        pass
    return data


def _perfil_next_shift_status(collab, today):
    data = {"next_shift_date": None, "next_shift_hour": None}
    try:
        ns = (
            Shift.query.filter(Shift.collaborator_id == collab.id, Shift.date >= today, Shift.shift_type != "folga")
            .order_by(Shift.date.asc())
            .first()
        )
        if ns:
            data["next_shift_date"] = ns.date
            if ns.start_dt:
                data["next_shift_hour"] = ns.start_dt.strftime("%H:%M")
            else:
                data["next_shift_hour"] = _perfil_shift_hour_guess(ns.shift_type)
    except Exception:
        pass
    return data


def _perfil_vacation_status(collab, today):
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    data = {
        "is_on_vacation": False,
        "vacation_end_date": None,
        "vacation_end_timestamp": 0,
        "vacation_return_hour": "05:00",
    }
    try:
        vacation = Vacation.query.filter(
            Vacation.collaborator_id == collab.id, Vacation.data_inicio <= today, Vacation.data_fim >= today
        ).first()
        if not vacation:
            return data

        data["is_on_vacation"] = True
        data["vacation_end_date"] = vacation.data_fim.strftime("%d/%m/%Y")
        return_date = vacation.data_fim + _td(days=1)
        return_date, return_hour = _perfil_vacation_return(collab, return_date)
        try:
            hour_parts = return_hour.split(":")
            return_hour_val = int(hour_parts[0]) if hour_parts else 5
            return_min_val = int(hour_parts[1]) if len(hour_parts) > 1 else 0
        except Exception:
            return_hour_val, return_min_val = 5, 0
        return_dt = _dt.combine(return_date, _dt.min.time().replace(hour=return_hour_val, minute=return_min_val))
        data["vacation_end_timestamp"] = int(return_dt.timestamp())
        data["vacation_return_hour"] = return_hour
    except Exception:
        pass
    return data


def _perfil_vacation_return(collab, return_date):
    try:
        next_shift = (
            Shift.query.filter(
                Shift.collaborator_id == collab.id, Shift.date >= return_date, Shift.shift_type != "folga"
            )
            .order_by(Shift.date.asc())
            .first()
        )
        if next_shift:
            hour = (
                next_shift.start_dt.strftime("%H:%M")
                if next_shift.start_dt
                else _perfil_shift_hour_guess(next_shift.shift_type)
            )
            return next_shift.date, hour
    except Exception:
        pass
    return return_date, "05:00"


def _perfil_medical_status(collab, today):
    from datetime import datetime as _dt

    data = {"is_on_medical": False, "medical_end_timestamp": 0, "medical_end_date": None}
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
            data["is_on_medical"] = True
            data["medical_end_date"] = mc.data_fim.strftime("%d/%m/%Y")
            med_end_dt = _dt.combine(mc.data_fim, _dt.min.time().replace(hour=23, minute=59, second=59))
            data["medical_end_timestamp"] = int(med_end_dt.timestamp())
    except Exception:
        pass
    return data


def _perfil_shift_hour_guess(shift_type: str):
    st = (shift_type or "").lower()
    if st.startswith("abertura"):
        return "05:00"
    if st == "tarde":
        return "09:30"
    if st.startswith("domingo"):
        return "05:00"
    return "05:00"


def _collect_logs():
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
    return logs


def _collaborators_with_display(q: str):
    try:
        colaboradores = Collaborator.query.order_by(Collaborator.name.asc()).all()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Erro ao buscar colaboradores: {e}", exc_info=True)
        colaboradores = []

    for c in colaboradores:
        try:
            c.display_name = _get_display_name(c)
        except Exception:
            c.display_name = ""

    if not q:
        return colaboradores, colaboradores

    try:
        filtrados = []
        q_lower = q.lower()
        for c in colaboradores:
            nome_busca = ""
            if c.user and c.user.name:
                nome_busca = c.user.name.lower()
            elif c.name:
                nome_busca = c.name.lower()
            if q_lower in nome_busca:
                filtrados.append(c)
        return colaboradores, filtrados
    except Exception:
        return colaboradores, colaboradores


def _get_display_name(collab):
    try:
        if collab.user_id and collab.user:
            return collab.user.name or ""
        return collab.name or ""
    except Exception:
        return ""


class _CollaboratorUser:
    """Wrapper para exibir usuários na página de gestão (com ou sem collaborator)"""

    def __init__(self, user=None, collaborator=None):
        self.id = user.id if user else (collaborator.id if collaborator else None)
        self.user = user
        self.collaborator = collaborator
        self.name = (user.name if user else collaborator.name) if (user or collaborator) else ""

    def __repr__(self):
        return f"<_CollaboratorUser {self.name}>"


def _all_users_for_display(q: str):
    """Retorna todos os usuários para a gestão (colaboradores + usuários sem collaborator)"""
    try:
        # Buscar todos os usuários
        all_users = User.query.order_by(User.name.asc()).all()
        # Criar lista de wrappers
        display_items = []
        for user in all_users:
            # Tenta encontrar um collaborator associado
            collab = Collaborator.query.filter_by(user_id=user.id).first()
            wrapper = _CollaboratorUser(user=user, collaborator=collab)
            display_items.append(wrapper)

        if not q:
            return display_items, display_items

        # Filtrar por query
        q_lower = q.lower()
        filtrados = [item for item in display_items if q_lower in item.name.lower()]
        return display_items, filtrados
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Erro ao buscar usuários para display: {e}", exc_info=True)
        return [], []


def _access_logs_context(acc_user: str):
    acc_page = _safe_int_arg("acc_page", 1)
    aq = SystemLog.query.filter(SystemLog.origem == "Acesso", SystemLog.evento == "login")
    if acc_user:
        aq = aq.filter(SystemLog.usuario.ilike(f"%{acc_user}%"))
    access_all = aq.order_by(SystemLog.data.desc()).all()
    access_page, acc_total_pages, acc_page = _paginate_list(access_all, acc_page, 10)
    return {
        "access_page": access_page,
        "acc_page": acc_page,
        "acc_total_pages": acc_total_pages,
    }


def _gestao_bank_context(colaboradores, per_page: int):
    from sqlalchemy import func

    bank_balances = {}
    saldo_collab = None
    saldo_hours = None
    saldo_days = None
    saldo_items = []
    saldo_start = None
    saldo_end = None

    try:
        sums = (
            db.session.query(TimeOffRecord.collaborator_id, func.coalesce(func.sum(TimeOffRecord.hours), 0.0))
            .filter(TimeOffRecord.record_type == "horas")
            .group_by(TimeOffRecord.collaborator_id)
            .all()
        )
        for cid, total in sums:
            bank_balances[int(cid)] = float(total or 0.0)

        scid = request.args.get("saldo_collaborator_id", type=int)
        saldo_start, saldo_end = _parse_saldo_dates()
        if scid:
            saldo_collab, saldo_hours, saldo_days, saldo_items = _saldo_details(scid, saldo_start, saldo_end)
    except Exception:
        bank_balances = {}

    recent_entries = _recent_hour_entries()
    folgas = _calculate_folgas(colaboradores)

    bh_collab_id = request.args.get("bh_collaborator_id", type=int)
    bh_page = _safe_int_arg("bh_page", 1)
    colaboradores_page, bh_total_pages, bh_page = _paginate_list(_bh_collaborators(bh_collab_id), bh_page, per_page)

    lc_collab_id = request.args.get("lc_collaborator_id", type=int)
    lc_page = _safe_int_arg("lc_page", 1)
    leave_credits_page, lc_total_pages, lc_page = _timeoff_page("folga_adicional", lc_collab_id, lc_page, per_page)

    la_collab_id = request.args.get("la_collaborator_id", type=int)
    la_page = _safe_int_arg("la_page", 1)
    leave_assignments_page, la_total_pages, la_page = _timeoff_page("folga_usada", la_collab_id, la_page, per_page)

    return {
        "bank_balances": bank_balances,
        "saldo_collab": saldo_collab,
        "saldo_hours": saldo_hours,
        "saldo_days": saldo_days,
        "saldo_items": saldo_items,
        "saldo_start": saldo_start,
        "saldo_end": saldo_end,
        "recent_entries": recent_entries,
        "folgas": folgas,
        "colaboradores_page": colaboradores_page,
        "bh_page": bh_page,
        "bh_total_pages": bh_total_pages,
        "bh_collab_id": bh_collab_id,
        "leave_credits_page": leave_credits_page,
        "lc_page": lc_page,
        "lc_total_pages": lc_total_pages,
        "lc_collab_id": lc_collab_id,
        "leave_assignments_page": leave_assignments_page,
        "la_page": la_page,
        "la_total_pages": la_total_pages,
        "la_collab_id": la_collab_id,
    }


def _parse_saldo_dates():
    try:
        raw_start = request.args.get("saldo_start", "") or ""
        raw_end = request.args.get("saldo_end", "") or ""
        from datetime import datetime as _dt2

        saldo_start = _dt2.strptime(raw_start.strip(), "%Y-%m-%d").date() if raw_start.strip() else None
        saldo_end = _dt2.strptime(raw_end.strip(), "%Y-%m-%d").date() if raw_end.strip() else None
        return saldo_start, saldo_end
    except Exception:
        return None, None


def _saldo_details(scid, saldo_start, saldo_end):
    from sqlalchemy import func

    try:
        saldo_collab = Collaborator.query.get(scid)
        if not saldo_collab:
            return None, None, None, []
        _reconcile_missing_credits(scid)
        horas_expr = func.case((TimeOffRecord.hours > 0, TimeOffRecord.hours), else_=0)
        horas_sum = func.coalesce(func.sum(horas_expr), 0.0)
        total_bruto_hours = float(
            db.session.query(horas_sum)
            .filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "horas")
            .scalar()
            or 0.0
        )
        days_from_hours = int(total_bruto_hours // 8.0) if total_bruto_hours >= 0.0 else 0
        saldo_hours = total_bruto_hours % 8.0 if total_bruto_hours >= 0.0 else 0.0
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
        saldo_days = int(credits_sum) + days_from_hours - int(assigned_sum) - int(converted_sum)
        saldo_items = _saldo_items(scid, saldo_start, saldo_end)
        return saldo_collab, saldo_hours, saldo_days, saldo_items
    except Exception:
        return None, None, None, []


def _reconcile_missing_credits(scid):
    from datetime import date as _date

    from sqlalchemy import func

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
    except Exception as e:
        _rollback_log_warning(e, "balance calculation")


def _saldo_items(scid, saldo_start, saldo_end):
    try:
        hq = TimeOffRecord.query.filter(TimeOffRecord.collaborator_id == scid, TimeOffRecord.record_type == "horas")
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
        items = []
        for e in h_list:
            items.append(
                {
                    "tipo": "horas",
                    "date": e.date,
                    "amount": float(e.hours or 0.0),
                    "unit": "h",
                    "motivo": e.notes or "",
                }
            )
        for c in c_list:
            items.append(
                {
                    "tipo": "credito",
                    "date": c.date,
                    "amount": int(c.days or 0),
                    "unit": "dia",
                    "motivo": (c.origin or "manual") + ((" — " + (c.notes or "")) if c.notes else ""),
                }
            )
        for a in a_list:
            items.append(
                {
                    "tipo": "uso",
                    "date": a.date,
                    "amount": -int(a.days or 0),
                    "unit": "dia",
                    "motivo": a.notes or "",
                }
            )
        items.sort(key=lambda x: x["date"], reverse=True)
        return items
    except Exception:
        return []


def _recent_hour_entries():
    try:
        return (
            TimeOffRecord.query.filter(TimeOffRecord.record_type == "horas")
            .order_by(TimeOffRecord.date.desc())
            .limit(50)
            .all()
        )
    except Exception:
        return []


def _calculate_folgas(colaboradores):
    from sqlalchemy import func

    folgas = []
    try:
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
    return folgas


def _bh_collaborators(bh_collab_id):
    bh_q = Collaborator.query.order_by(Collaborator.name.asc())
    if bh_collab_id:
        bh_q = bh_q.filter(Collaborator.id == bh_collab_id)
    return bh_q.all()


def _timeoff_page(record_type: str, collab_id, page: int, per_page: int):
    q = TimeOffRecord.query.filter(TimeOffRecord.record_type == record_type).order_by(TimeOffRecord.date.desc())
    if collab_id:
        q = q.filter(TimeOffRecord.collaborator_id == collab_id)
    all_items = q.all()
    return _paginate_list(all_items, page, per_page)


def _vps_storage_info():
    try:
        root = str(current_app.root_path or os.getcwd())
        du = shutil.disk_usage(root)
        uptime_str = _uptime_string()
        load_str = _load_average_string()

        def _fmt_bytes(n: int) -> str:
            units = ["B", "KB", "MB", "GB", "TB", "PB"]
            f = float(n)
            for u in units:
                if f < 1024.0:
                    return f"{f:.1f} {u}"
                f = f / 1024.0
            return f"{f:.1f} EB"

        return {
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
        return None


def _uptime_string():
    try:
        with open("/proc/uptime", "r") as f:
            secs = float((f.read().split()[0] or "0").strip())
        days = int(secs // 86400)
        rem = secs % 86400
        hours = int(rem // 3600)
        minutes = int((rem % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except Exception:
        try:
            uptime_cmd = "/usr/bin/uptime"
            if os.path.exists(uptime_cmd):
                out = subprocess.check_output([uptime_cmd, "-p"], timeout=2)
                return (out.decode("utf-8", errors="ignore") or "").strip()
        except Exception:
            return None
    return None


def _load_average_string():
    try:
        import os as _os

        la_fn = getattr(_os, "getloadavg", None)
        if callable(la_fn):
            lv = cast(Sequence[float], la_fn())
            a = float(lv[0])
            b = float(lv[1])
            c = float(lv[2])
            return f"{a:.2f}, {b:.2f}, {c:.2f}"
        with open("/proc/loadavg", "r") as f:
            parts = f.read().split()
            it = iter(parts)
            a = next(it, None)
            b = next(it, None)
            c = next(it, None)
            if a is not None and b is not None and c is not None:
                aa = float(a)
                bb = float(b)
                cc = float(c)
                return f"{aa:.2f}, {bb:.2f}, {cc:.2f}"
    except Exception:
        return None
    return None


def _update_collaborator_basic_fields(collab):
    collab.name = ((request.form.get("name") or collab.name or "").strip()) or collab.name
    role_in = request.form.get("role")
    collab.role = ((role_in or collab.role or "").strip()) or None
    active_str = request.form.get("active", "on") or "on"
    collab.active = active_str.lower() in ("on", "true", "1")
    collab.regular_team = _team_value(request.form.get("regular_team"), collab.regular_team)
    collab.sunday_team = _team_value(request.form.get("sunday_team"), collab.sunday_team)
    collab.special_team = _team_value(request.form.get("special_team"), collab.special_team)
    setor_id = request.form.get("setor_id", type=int)
    collab.setor_id = setor_id


def _team_value(value, current):
    val = (value or current or "").strip()
    return (val or None) if val in ("1", "2") else None


def _handle_collaborator_user(collab, username: str, password: str, nivel: str):
    if collab.user_id:
        user = User.query.get(collab.user_id)
        if user:
            _update_existing_user(user, collab, username, password, nivel)
            return
    _create_user_for_collaborator(collab, username, password, nivel)


def _update_existing_user(user, collab, username: str, password: str, nivel: str):
    if nivel and nivel in ("admin", "DEV") and current_user.nivel != "DEV":
        flash("Apenas desenvolvedores podem alterar usuários para nível Gerente ou Desenvolvedor.", "danger")
        raise ValueError("Nivel não permitido")
    if user.username != username and User.query.filter(User.username == username, User.id != user.id).first():
        flash(f'Login "{username}" já existe.', "danger")
        raise ValueError("Login duplicado")
    user.name = collab.name
    user.username = username
    if password:
        user.password_hash = generate_password_hash(password)
    if nivel:
        user.nivel = nivel


def _create_user_for_collaborator(collab, username: str, password: str, nivel: str):
    if User.query.filter_by(username=username).first():
        flash(f'Login "{username}" já existe.', "danger")
        raise ValueError("Login duplicado")
    nivel_final = nivel or "visualizador"
    if nivel_final in ("admin", "DEV") and current_user.nivel != "DEV":
        flash("Apenas desenvolvedores podem criar usuários com nível Gerente ou Desenvolvedor.", "danger")
        raise ValueError("Nivel não permitido")
    user = User()
    user.name = collab.name
    user.username = username
    user.password_hash = generate_password_hash(password) if password else generate_password_hash("123456")
    user.nivel = nivel_final
    db.session.add(user)
    db.session.flush()
    collab.user_id = user.id


def _reconcile_after_hour_delete(cid):
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
        _remove_excess_credits(cid, auto_credits - desired_credits)
        return True
    if auto_credits < desired_credits:
        _add_missing_credits(cid, desired_credits - auto_credits)
        return True
    return False


def _remove_excess_credits(cid, excess):
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
        _compensate_missing_adjustments(cid, excess - removed_adj)
    flash(
        (f"Lançamento excluído. Conversões automáticas revertidas: " f"-{excess} dia(s) e +{excess*8}h no banco."),
        "warning",
    )


def _compensate_missing_adjustments(cid, missing_adj):
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


def _add_missing_credits(cid, missing):
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
        (f"Lançamento excluído. Conversões automáticas ajustadas: " f"+{missing} dia(s) e -{missing*8}h no banco."),
        "info",
    )


def _run_setup_script():
    root = Path(current_app.root_path).resolve()
    run_script = (root / "vps_setup.sh") if (root / "vps_setup.sh").exists() else (root / "scripts" / "vps_setup.sh")
    if run_script.exists():
        subprocess.Popen(["bash", str(run_script)], cwd=str(root))


def _run_reboot():
    cmd = (os.getenv("VPS_REBOOT_CMD") or "sudo").strip()
    if not cmd:
        return
    args = cmd.split()
    if args[-1] == "reboot":
        subprocess.Popen(["sudo", "reboot"])
    else:
        subprocess.Popen(args)


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
                args = cmd.split()
                subprocess.Popen(args)
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
        # Remover registros relacionados antes de excluir o usuário
        # 1. Desvincular colaborador (setar user_id como NULL)
        Collaborator.query.filter_by(user_id=user_id).update({"user_id": None})

        # 2. Remover registros de login
        UserLogin.query.filter_by(user_id=user_id).delete()

        # 3. Remover votos de artigos
        ArticleVote.query.filter_by(user_id=user_id).delete()

        # 4. Remover votos de sugestões
        SuggestionVote.query.filter_by(user_id=user_id).delete()

        # 5. Remover notificações lidas
        NotificationRead.query.filter_by(user_id=user_id).delete()

        # 6. Atualizar recepções de carne (setar recebedor_id como NULL)
        MeatReception.query.filter_by(recebedor_id=user_id).update({"recebedor_id": None})

        # 7. Atualizar mudanças de registro de jornada (setar changed_by como NULL)
        RegistroJornadaChange.query.filter_by(changed_by=user_id).update({"changed_by": None})

        # Agora podemos excluir o usuário com segurança
        db.session.delete(user)

        log = SystemLog()
        log.origem = "Usuarios"
        log.evento = "excluir"
        log.detalhes = f"Excluido {user.name} ({user.username})"
        log.usuario = current_user.name
        db.session.add(log)
        db.session.commit()
        flash(f'Usuário "{user.name}" excluído com sucesso.', "success")
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
        return _handle_perfil_post()

    _ensure_collaborator_schema()
    collab, balance_data, entries = _perfil_collaborator_payload()

    residual_hours = balance_data["horas_restantes"] if balance_data else 0.0
    dias_completos = balance_data["dias_completos"] if balance_data else 0
    collaborator_values, day_value = _perfil_values(collab, balance_data)
    status = _perfil_status_flags(collab)

    return render_template(
        "perfil.html",
        active_page="perfil",
        collab=collab,
        balance_data=balance_data,
        entries=entries,
        residual_hours=residual_hours,
        dias_completos=dias_completos,
        collaborator_values=collaborator_values,
        day_value=day_value,
        **status,
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
    _ensure_collaborator_schema()

    u_page = _safe_int_arg("u_page", 1)
    l_page = _safe_int_arg("l_page", 1)
    logs = _collect_logs()
    logs_page, l_total_pages, l_page = _paginate_list(logs, l_page, 2)

    # Buscar todos os usuários (com ou sem collaborator)
    all_users_list, filtered_users = _all_users_for_display(q)
    users_page, u_total_pages, u_page = _paginate_list(filtered_users, u_page, 5)
    all_users = User.query.all()

    acc_user = (request.args.get("acc_user") or "").strip()
    access_ctx = _access_logs_context(acc_user)

    senha_sugestao = "123456"
    roles = JobRole.query.order_by(JobRole.name.asc()).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome.asc()).all()

    # Buscar colaboradores para o banco de horas (apenas que têm collaborator)
    colaboradores_colab = Collaborator.query.order_by(Collaborator.name.asc()).all()
    for c in colaboradores_colab:
        try:
            c.display_name = _get_display_name(c)
        except Exception:
            c.display_name = ""

    bank_ctx = _gestao_bank_context(colaboradores_colab, per_page=10)
    vps_storage = _vps_storage_info()

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
        setores=setores,
        colaboradores=colaboradores_colab,
        folgas=bank_ctx["folgas"],
        users=all_users,
        bank_balances=bank_ctx["bank_balances"],
        recent_entries=bank_ctx["recent_entries"],
        access_page=access_ctx["access_page"],
        acc_page=access_ctx["acc_page"],
        acc_total_pages=access_ctx["acc_total_pages"],
        acc_user=acc_user,
        saldo_collab=bank_ctx["saldo_collab"],
        saldo_hours=bank_ctx["saldo_hours"],
        saldo_days=bank_ctx["saldo_days"],
        saldo_items=bank_ctx["saldo_items"],
        saldo_start=bank_ctx["saldo_start"],
        saldo_end=bank_ctx["saldo_end"],
        vps_storage=vps_storage,
        colaboradores_page=bank_ctx["colaboradores_page"],
        bh_page=bank_ctx["bh_page"],
        bh_total_pages=bank_ctx["bh_total_pages"],
        bh_collab_id=bank_ctx["bh_collab_id"],
        leave_credits_page=bank_ctx["leave_credits_page"],
        lc_page=bank_ctx["lc_page"],
        lc_total_pages=bank_ctx["lc_total_pages"],
        lc_collab_id=bank_ctx["lc_collab_id"],
        leave_assignments_page=bank_ctx["leave_assignments_page"],
        la_page=bank_ctx["la_page"],
        la_total_pages=bank_ctx["la_total_pages"],
        la_collab_id=bank_ctx["la_collab_id"],
    )


@bp.route("/gestao/colaboradores/criar", methods=["POST"])
@login_required
def gestao_colabs_criar():
    """Cria colaborador e usuário juntos (são uma coisa só)"""
    setor_id = request.form.get("setor_id", type=int)
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
        c.setor_id = setor_id
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
        _update_collaborator_basic_fields(c)
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        nivel = request.form.get("nivel", "").strip()
        if username:
            _handle_collaborator_user(c, username, password, nivel)
        db.session.commit()
        flash("Colaborador atualizado.", "info")
    except Exception as e:
        db.session.rollback()
        if not isinstance(e, ValueError):
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


@bp.route("/gestao/usuarios/<int:user_id>/criar-colaborador", methods=["POST"])
@login_required
def gestao_usuario_criar_colaborador(user_id: int):
    """Cria um Collaborator para um usuário existente (usuário cadastrado via login)"""
    if current_user.nivel not in ("admin", "DEV"):
        flash("Você não tem permissão para criar colaboradores.", "danger")
        return redirect(url_for("usuarios.gestao"))

    user = User.query.get(user_id)
    if not user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("usuarios.gestao"))

    # Verificar se já tem um Collaborator
    existing = Collaborator.query.filter_by(user_id=user.id).first()
    if existing:
        flash("Este usuário já tem um Collaborator associado.", "warning")
        return redirect(url_for("usuarios.gestao"))

    try:
        # Criar novo Collaborator
        new_collab = Collaborator()
        new_collab.name = user.name
        new_collab.user_id = user.id
        new_collab.active = True

        # Aplicar setor se fornecido
        setor_id = request.form.get("setor_id", type=int)
        if setor_id:
            setor = Setor.query.get(setor_id)
            if setor:
                new_collab.setor_id = setor_id

        db.session.add(new_collab)
        db.session.commit()

        flash(f"Collaborator criado para {user.name}. Agora pode ser gerenciado na página de ciclos.", "success")
        return redirect(url_for("usuarios.gestao"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar Collaborator: {e}", "danger")
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
        except Exception as e:
            flash(f"Erro ao registrar horas: {e}", "danger")
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
            msg = (
                f"Nenhuma conversão necessária. O colaborador {collaborator.name} já tem todas as "
                f"horas convertidas em dias (total bruto: {total_bruto_hours:.2f}h = "
                f"{desired_credits} dia(s) já convertido(s))."
            )
            flash(msg, "info")
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
            msg = (
                f"Atenção: A conversão foi limitada a {allowed_credits} dia(s) para não ultrapassar "
                f"o limite de {max_allowed_days} dias. Saldo atual: {current_balance} dias, "
                f"após conversão: {current_balance + allowed_credits} dias."
            )
            flash(msg, "warning")

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
        handled = _reconcile_after_hour_delete(cid)
        if not handled:
            flash("Lançamento excluído.", "success")
    except Exception:
        try:
            db.session.rollback()
        except Exception as e:
            flash(f"Erro ao excluir lançamento: {e}", "danger")
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
