"""Rotas de PDF para o módulo Jornada usando WeasyPrint"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, make_response, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import db
from ..models import Collaborator, JornadaArchive, MonthStatus, TimeOffRecord
from .jornada import _calculate_collaborator_balance, _get_all_collaborators, _get_collaborator_display_name

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except Exception:
    # Captura ImportError, OSError e outros erros de inicialização do WeasyPrint
    # (especialmente no Windows onde DLLs podem não estar disponíveis)
    WEASYPRINT_AVAILABLE = False
    HTML = None  # type: ignore

bp = Blueprint("jornada_pdf", __name__, url_prefix="/jornada/pdf")


@bp.route("/em-aberto", methods=["GET"], strict_slashes=False)
@login_required
def em_aberto():
    """Gera PDF da página principal de Jornada"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível. Instale com: pip install weasyprint", "danger")
        return redirect(url_for("jornada.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    try:
        # Buscar todos os registros (não arquivados)
        records = TimeOffRecord.query.order_by(TimeOffRecord.date.desc(), TimeOffRecord.id.desc()).limit(500).all()

        colaboradores = _get_all_collaborators()
        all_stats = []
        for colab in colaboradores:
            balance = _calculate_collaborator_balance(colab.id)
            all_stats.append(
                {"collaborator": colab, "display_name": _get_collaborator_display_name(colab), "balance": balance}
            )

        total_horas = sum(float(s["balance"].get("total_bruto_hours", 0.0)) for s in all_stats)
        total_horas_residuais = sum(float(s["balance"].get("residual_hours", 0.0)) for s in all_stats)
        total_saldo_folgas = sum(int(s["balance"].get("saldo_days", 0)) for s in all_stats)
        total_folgas_usadas = sum(int(s["balance"].get("assigned_sum", 0)) for s in all_stats)
        total_conversoes = sum(int(s["balance"].get("converted_sum", 0)) for s in all_stats)

        html = render_template(
            "jornada/pdf/em_aberto.html",
            records=records,
            all_stats=all_stats,
            meses_abertos=[],
            total_horas=total_horas,
            total_horas_residuais=total_horas_residuais,
            total_saldo_folgas=total_saldo_folgas,
            total_folgas_usadas=total_folgas_usadas,
            total_conversoes=total_conversoes,
            generated_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        pdf = HTML(string=html).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers[
            "Content-Disposition"
        ] = f'inline; filename=jornada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for("jornada.index"))


@bp.route("/fechado-revisao", methods=["GET"], strict_slashes=False)
@login_required
def fechado_revisao():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("jornada.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    # Redirecionar para a página principal simplificada
    return redirect(url_for("jornada.index"))


@bp.route("/arquivados", methods=["GET"], strict_slashes=False)
@login_required
def arquivados():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("jornada.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    # Redirecionar para a página principal simplificada
    return redirect(url_for("jornada.index"))


@bp.route("/situacao-final", methods=["GET"], strict_slashes=False)
@login_required
def situacao_final():
    """Gera PDF da página principal de Jornada (compatibilidade)"""
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("jornada.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    # Redirecionar para a página principal simplificada
    return redirect(url_for("jornada.index"))
