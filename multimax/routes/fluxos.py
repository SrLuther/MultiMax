from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import CentralColaborador, CentralVacation, Fluxo, FluxoArquivo, FluxoCiclo, FluxoConfig, FluxoLancamento

try:
    from weasyprint import HTML  # type: ignore

    WEASYPRINT_AVAILABLE = True
except Exception:
    HTML = None
    WEASYPRINT_AVAILABLE = False

bp = Blueprint("fluxos", __name__, url_prefix="/fluxos")

VALOR_HORA_DIA = Decimal("8")
VALID_DESCRICOES = {"Domingo", "Folga", "Feriado", "Outro"}


def _month_bounds(ref: date) -> tuple[date, date]:
    start = ref.replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start, end


def _week_bounds(ref: date) -> tuple[date, date]:
    # Semana começa no domingo
    days_since_sunday = (ref.weekday() + 1) % 7
    start = ref - timedelta(days=days_since_sunday)
    end = start + timedelta(days=6)
    return start, end


def _weekly_cycles_for_month(start: date, end: date) -> list[dict[str, Any]]:
    cycles = []
    cursor = start
    week_start, week_end = _week_bounds(cursor)
    # garantir ciclo que intersecta o mês
    while week_end < start:
        week_start += timedelta(days=7)
        week_end += timedelta(days=7)
    index = 1
    while week_start <= end:
        cycles.append(
            {
                "label": f"Ciclo {index}",
                "week_start": week_start,
                "week_end": week_end,
            }
        )
        index += 1
        week_start += timedelta(days=7)
        week_end += timedelta(days=7)
    return cycles


def _get_or_create_config() -> FluxoConfig:
    config = FluxoConfig.query.first()
    if not config:
        config = FluxoConfig(valor_diaria=0)
        db.session.add(config)
        db.session.commit()
    return config


def _get_or_create_fluxo(ref: date) -> Fluxo:
    mes_ano = ref.strftime("%Y-%m")
    fluxo = Fluxo.query.filter_by(mes_ano=mes_ano).first()
    if fluxo:
        return fluxo

    start, end = _month_bounds(ref)
    config = _get_or_create_config()
    fluxo = Fluxo(
        mes_ano=mes_ano,
        data_inicio=start,
        data_fim=end,
        status="aberto",
        valor_diaria=config.valor_diaria,
    )
    db.session.add(fluxo)
    db.session.flush()

    for cycle in _weekly_cycles_for_month(start, end):
        db.session.add(
            FluxoCiclo(
                fluxo_id=fluxo.id,
                week_start=cycle["week_start"],
                week_end=cycle["week_end"],
                label=cycle["label"],
            )
        )

    db.session.commit()
    return fluxo


def _get_or_create_ciclo(fluxo: Fluxo, lanc_date: date) -> FluxoCiclo:
    week_start, week_end = _week_bounds(lanc_date)
    ciclo = (
        FluxoCiclo.query.filter_by(fluxo_id=fluxo.id)
        .filter(FluxoCiclo.week_start == week_start, FluxoCiclo.week_end == week_end)
        .first()
    )
    if ciclo:
        return ciclo
    # Criar ciclo (caso data extrapole ciclos existentes)
    label_index = FluxoCiclo.query.filter_by(fluxo_id=fluxo.id).count() + 1
    ciclo = FluxoCiclo(fluxo_id=fluxo.id, week_start=week_start, week_end=week_end, label=f"Ciclo {label_index}")
    db.session.add(ciclo)
    db.session.commit()
    return ciclo


def _get_fluxos_archive_dir(kind: str) -> str:
    base_dir = os.path.join(os.getcwd(), "instance", "fluxos", "arquivo_morto", kind)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def _list_pdf_files(base_dir: str, query: str) -> list[dict[str, Any]]:
    arquivos = []
    for name in sorted(os.listdir(base_dir)):
        if not name.lower().endswith(".pdf"):
            continue
        if query and query not in name.lower():
            continue
        full_path = os.path.join(base_dir, name)
        if not os.path.isfile(full_path):
            continue
        stat = os.stat(full_path)
        arquivos.append(
            {
                "name": name,
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, ZoneInfo("America/Sao_Paulo")),
            }
        )
    return arquivos


def _fluxo_referencia_label(fluxo: Fluxo) -> str:
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    ref_date = fluxo.data_inicio or date.today()
    mes_nome = meses[ref_date.month - 1]
    return f"{mes_nome}{ref_date.year}"


def _summaries(fluxo: Fluxo, colaboradores: list[CentralColaborador]) -> dict[int, dict[str, Any]]:
    summaries: dict[int, dict[str, Any]] = {}
    for c in colaboradores:
        lancs = FluxoLancamento.query.filter_by(fluxo_id=fluxo.id, collaborator_id=c.id).all()
        total_pos = sum(lanc.horas for lanc in lancs if lanc.horas > 0)
        total_neg = sum(abs(lanc.horas) for lanc in lancs if lanc.horas < 0)
        restante = total_pos - total_neg
        horas_base = restante if restante > 0 else 0
        dias_completos = int(horas_base // 8)
        valor_diaria = float(fluxo.valor_diaria or 0)
        valor_receber = dias_completos * valor_diaria
        summaries[c.id] = {
            "total_horas": round(total_pos, 2),
            "horas_utilizadas": round(total_neg, 2),
            "dias_completos": dias_completos,
            "restante": round(restante, 2),
            "valor_receber": round(valor_receber, 2),
        }
    return summaries


def _group_history(fluxo: Fluxo, collaborator_id: int) -> list[dict[str, Any]]:
    ciclos = FluxoCiclo.query.filter_by(fluxo_id=fluxo.id).order_by(FluxoCiclo.week_start.asc()).all()
    grupos = []
    for c in ciclos:
        lancs = (
            FluxoLancamento.query.filter_by(fluxo_id=fluxo.id, ciclo_id=c.id, collaborator_id=collaborator_id)
            .order_by(FluxoLancamento.data.asc(), FluxoLancamento.id.asc())
            .all()
        )
        grupos.append({"ciclo": c, "lancamentos": lancs})
    return grupos


def _actor_name() -> str:
    return getattr(current_user, "nome", None) or getattr(current_user, "name", None) or current_user.username


def _is_on_vacation(collaborator_id: int, dia_data: date) -> bool:
    try:
        v = CentralVacation.query.filter(
            CentralVacation.collaborator_id == collaborator_id,
            CentralVacation.ativo.is_(True),
            CentralVacation.data_inicio <= dia_data,
            CentralVacation.data_fim >= dia_data,
        ).first()
        return v is not None
    except Exception:
        return False


def _get_vacations_for_fluxo(collaborator_id: int, fluxo: Fluxo) -> list[CentralVacation]:
    try:
        return (
            CentralVacation.query.filter(
                CentralVacation.collaborator_id == collaborator_id,
                CentralVacation.ativo.is_(True),
                CentralVacation.data_inicio <= fluxo.data_fim,
                CentralVacation.data_fim >= fluxo.data_inicio,
            )
            .order_by(CentralVacation.data_inicio.asc())
            .all()
        )
    except Exception:
        return []


def _validar_lancamento(descricao: str, data_lanc: date, horas: float, observacao: str) -> str | None:
    if descricao not in VALID_DESCRICOES:
        return "Descrição inválida."
    if descricao == "Domingo" and data_lanc.weekday() != 6:
        return "A data não corresponde a um Domingo."
    if descricao == "Folga":
        if horas != -8:
            return "Para Folga, as horas devem ser -8."
        if horas >= 0:
            return "Para Folga, as horas devem ser um valor negativo."
    if descricao == "Outro" and not observacao.strip():
        return "Para Outro, preencha o campo Observações com a descrição."
    return None


@bp.route("/", methods=["GET"])
@login_required
def index():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("home.index"))

    fluxo = _get_or_create_fluxo(date.today())
    colaboradores = CentralColaborador.query.order_by(CentralColaborador.nome.asc()).all()
    summaries = _summaries(fluxo, colaboradores)

    historicos = {c.id: _group_history(fluxo, c.id) for c in colaboradores}
    ferias_map = {c.id: _get_vacations_for_fluxo(c.id, fluxo) for c in colaboradores}
    total_horas = sum(s["total_horas"] for s in summaries.values())
    total_dias = sum(s["dias_completos"] for s in summaries.values())
    total_descontos = sum(s["horas_utilizadas"] for s in summaries.values())
    total_restante = sum(s["restante"] for s in summaries.values())
    total_valor = sum(s["valor_receber"] for s in summaries.values())

    return render_template(
        "fluxos/index.html",
        fluxo=fluxo,
        colaboradores=colaboradores,
        summaries=summaries,
        historicos=historicos,
        ferias_map=ferias_map,
        total_horas=total_horas,
        total_dias=total_dias,
        total_descontos=total_descontos,
        total_restante=total_restante,
        total_valor=total_valor,
    )


@bp.route("/arquivos", methods=["GET"], strict_slashes=False)
@login_required
def arquivos_index():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    query = (request.args.get("q") or "").strip().lower()
    uploads_dir = _get_fluxos_archive_dir("uploads")
    fluxos_dir = _get_fluxos_archive_dir("fluxos")

    uploads = _list_pdf_files(uploads_dir, query)
    fluxos = _list_pdf_files(fluxos_dir, query)

    return render_template(
        "fluxos/arquivos.html",
        uploads=uploads,
        fluxos=fluxos,
        query=query,
    )


@bp.route("/arquivos/upload", methods=["POST"], strict_slashes=False)
@login_required
def arquivos_upload():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.arquivos_index"))

    if "pdf" not in request.files:
        flash("Nenhum arquivo enviado.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    pdf = request.files["pdf"]
    if not pdf or not pdf.filename:
        flash("Arquivo inválido.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    if "." not in pdf.filename or pdf.filename.rsplit(".", 1)[1].lower() != "pdf":
        flash("Envie apenas arquivos PDF.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    try:
        from ..filename_utils import secure_filename

        archive_dir = _get_fluxos_archive_dir("uploads")
        pdf.seek(0, 2)
        size = pdf.tell()
        pdf.seek(0)
        if size > 20 * 1024 * 1024:
            flash("Arquivo muito grande. Máximo 20MB.", "warning")
            return redirect(url_for("fluxos.arquivos_index"))

        safe_name = secure_filename(pdf.filename)
        timestamp = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{safe_name}"
        pdf.save(os.path.join(archive_dir, filename))
        flash("PDF enviado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar PDF: {e}", "danger")

    return redirect(url_for("fluxos.arquivos_index"))


@bp.route("/arquivos/arquivo/<path:name>", methods=["GET"], strict_slashes=False)
@login_required
def arquivos_download(name: str):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.arquivos_index"))

    tipo = (request.args.get("tipo") or "uploads").strip().lower()
    if tipo not in ("uploads", "fluxos"):
        flash("Arquivo inválido.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    archive_dir = _get_fluxos_archive_dir(tipo)
    safe_name = os.path.basename(name)
    if not safe_name.lower().endswith(".pdf"):
        flash("Arquivo inválido.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    full_path = os.path.join(archive_dir, safe_name)
    if not os.path.isfile(full_path):
        flash("Arquivo não encontrado.", "warning")
        return redirect(url_for("fluxos.arquivos_index"))

    mode = (request.args.get("mode") or "").strip().lower()
    if mode == "view":
        as_attach = False
    else:
        as_attach = True

    return send_file(full_path, as_attachment=as_attach, attachment_filename=safe_name, mimetype="application/pdf")


@bp.route("/ferias/adicionar", methods=["POST"], strict_slashes=False)
@login_required
def ferias_adicionar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    try:
        cid_str: str = (request.form.get("collaborator_id") or "").strip()
        di_str: str = (request.form.get("data_inicio") or "").strip()
        df_str: str = (request.form.get("data_fim") or "").strip()
        if not cid_str or not di_str or not df_str:
            flash("Dados obrigatórios ausentes.", "warning")
            return redirect(url_for("fluxos.index"))

        cid = int(cid_str)
        data_inicio: date = datetime.strptime(di_str, "%Y-%m-%d").date()
        data_fim: date = datetime.strptime(df_str, "%Y-%m-%d").date()

        if data_fim < data_inicio:
            flash("Data final deve ser maior ou igual à data inicial.", "warning")
            return redirect(url_for("fluxos.index"))

        v = CentralVacation()
        v.collaborator_id = cid
        v.data_inicio = data_inicio
        v.data_fim = data_fim
        v.criado_por = _actor_name()
        db.session.add(v)
        db.session.commit()
        flash("Férias registradas com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao registrar férias: {e}", "danger")

    return redirect(url_for("fluxos.index"))


@bp.route("/config/valor-diaria", methods=["POST"])
@login_required
def atualizar_valor_diaria():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    valor_raw = (request.form.get("valor_diaria") or "0").replace(",", ".")
    try:
        valor = Decimal(valor_raw)
    except Exception:
        flash("Valor inválido.", "warning")
        return redirect(url_for("fluxos.index"))

    config = _get_or_create_config()
    config.valor_diaria = valor
    config.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))

    fluxo = _get_or_create_fluxo(date.today())
    fluxo.valor_diaria = valor
    fluxo.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))

    db.session.commit()
    flash("Valor da diária atualizado.", "success")
    return redirect(url_for("fluxos.index"))


@bp.route("/lancamentos/novo", methods=["POST"])
@login_required
def novo_lancamento():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    fluxo = _get_or_create_fluxo(date.today())
    collaborator_id = int(request.form.get("collaborator_id") or 0)
    horas = float((request.form.get("horas") or "0").replace(",", "."))
    descricao = (request.form.get("descricao") or "").strip()
    data_str = (request.form.get("data") or "").strip()
    observacao = (request.form.get("observacao") or "").strip()

    if not collaborator_id or not descricao or not data_str:
        flash("Preencha colaborador, descrição e data.", "warning")
        return redirect(url_for("fluxos.index"))

    try:
        data_lanc = datetime.strptime(data_str, "%Y-%m-%d").date()
    except Exception:
        flash("Data inválida.", "warning")
        return redirect(url_for("fluxos.index"))

    if _is_on_vacation(collaborator_id, data_lanc):
        flash("Colaborador está de férias neste período. Não é possível registrar lançamentos.", "warning")
        return redirect(url_for("fluxos.index"))

    erro_validacao = _validar_lancamento(descricao, data_lanc, horas, observacao)
    if erro_validacao:
        flash(erro_validacao, "warning")
        return redirect(url_for("fluxos.index"))

    ciclo = _get_or_create_ciclo(fluxo, data_lanc)

    lanc = FluxoLancamento(
        fluxo_id=fluxo.id,
        ciclo_id=ciclo.id,
        collaborator_id=collaborator_id,
        data=data_lanc,
        horas=horas,
        descricao=descricao,
        observacao=observacao or None,
        created_by=_actor_name(),
    )
    db.session.add(lanc)
    db.session.commit()

    flash("Lançamento registrado.", "success")
    return redirect(url_for("fluxos.index"))


@bp.route("/lancamentos/<int:lanc_id>/editar", methods=["POST"])
@login_required
def editar_lancamento(lanc_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    lanc = db.session.get(FluxoLancamento, lanc_id)
    if not lanc:
        abort(404)

    horas = float((request.form.get("horas") or lanc.horas).replace(",", "."))
    descricao = (request.form.get("descricao") or lanc.descricao).strip()
    data_str = (request.form.get("data") or lanc.data.strftime("%Y-%m-%d")).strip()
    observacao = (request.form.get("observacao") or "").strip()

    try:
        data_lanc = datetime.strptime(data_str, "%Y-%m-%d").date()
    except Exception:
        flash("Data inválida.", "warning")
        return redirect(url_for("fluxos.index"))

    if _is_on_vacation(lanc.collaborator_id, data_lanc):
        flash("Colaborador está de férias neste período. Não é possível alterar lançamentos.", "warning")
        return redirect(url_for("fluxos.index"))

    erro_validacao = _validar_lancamento(descricao, data_lanc, horas, observacao)
    if erro_validacao:
        flash(erro_validacao, "warning")
        return redirect(url_for("fluxos.index"))

    fluxo = db.session.get(Fluxo, lanc.fluxo_id)
    if fluxo:
        ciclo = _get_or_create_ciclo(fluxo, data_lanc)
        lanc.ciclo_id = ciclo.id

    lanc.horas = horas
    lanc.descricao = descricao
    lanc.data = data_lanc
    lanc.observacao = observacao or None
    lanc.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    db.session.commit()

    flash("Lançamento atualizado.", "success")
    return redirect(url_for("fluxos.index"))


@bp.route("/lancamentos/<int:lanc_id>/excluir", methods=["POST"])
@login_required
def excluir_lancamento(lanc_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    lanc = db.session.get(FluxoLancamento, lanc_id)
    if not lanc:
        abort(404)

    if _is_on_vacation(lanc.collaborator_id, lanc.data):
        flash("Colaborador está de férias neste período. Não é possível remover lançamentos.", "warning")
        return redirect(url_for("fluxos.index"))

    db.session.delete(lanc)
    db.session.commit()
    flash("Lançamento removido.", "info")
    return redirect(url_for("fluxos.index"))


@bp.route("/pdf/individual/<int:collaborator_id>", methods=["GET"], strict_slashes=False)
@login_required
def pdf_individual(collaborator_id: int):
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("fluxos.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    fluxo = _get_or_create_fluxo(date.today())
    collaborator = db.session.get(CentralColaborador, collaborator_id)
    if not collaborator:
        abort(404)
    historicos = _group_history(fluxo, collaborator_id)
    summaries = _summaries(fluxo, [collaborator])
    summary = summaries.get(collaborator.id, {})

    try:
        import sys

        base_dir: Any | str = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        logo_header_path: str = os.path.join(base_dir, "static", "icons", "logo black.png")
        if os.path.exists(logo_header_path):
            logo_header: str = os.path.relpath(logo_header_path, base_dir).replace("\\", "/")
        else:
            logo_header = ""

        html = render_template(
            "fluxos/pdf_individual.html",
            collaborator=collaborator,
            historicos=historicos,
            fluxo=fluxo,
            summary=summary,
            logo_header=logo_header,
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        base_url: str = str(base_dir) if base_dir else os.getcwd()
        assert HTML is not None
        pdf: bytes | None = HTML(string=html, base_url=base_url).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f'inline; filename=fluxo_{fluxo.mes_ano}_{collaborator.nome.replace(" ", "_")}.pdf'
        )
        return response
    except Exception as e:
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for("fluxos.index"))


@bp.route("/pdf/geral", methods=["GET"], strict_slashes=False)
@login_required
def pdf_geral():
    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("fluxos.index"))

    if current_user.nivel not in ["operador", "admin", "DEV"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    fluxo = _get_or_create_fluxo(date.today())
    colaboradores = CentralColaborador.query.order_by(CentralColaborador.nome.asc()).all()
    summaries = _summaries(fluxo, colaboradores)
    historicos = {c.id: _group_history(fluxo, c.id) for c in colaboradores}

    total_horas = sum(s["total_horas"] for s in summaries.values())
    total_dias = sum(s["dias_completos"] for s in summaries.values())
    total_descontos = sum(s["horas_utilizadas"] for s in summaries.values())
    total_restante = sum(s["restante"] for s in summaries.values())
    total_valor = sum(s["valor_receber"] for s in summaries.values())

    try:
        import sys

        base_dir: Any | str = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        logo_header_path: str = os.path.join(base_dir, "static", "icons", "logo black.png")
        if os.path.exists(logo_header_path):
            logo_header: str = os.path.relpath(logo_header_path, base_dir).replace("\\", "/")
        else:
            logo_header = ""

        html = render_template(
            "fluxos/pdf_geral.html",
            fluxo=fluxo,
            colaboradores=colaboradores,
            summaries=summaries,
            historicos=historicos,
            total_horas=total_horas,
            total_dias=total_dias,
            total_descontos=total_descontos,
            total_restante=total_restante,
            total_valor=total_valor,
            nome_empresa="MultiMax",
            valor_diaria=float(fluxo.valor_diaria or 0),
            logo_header=logo_header,
            logo_footer=logo_header,
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        base_url: str = str(base_dir) if base_dir else os.getcwd()
        assert HTML is not None
        pdf: bytes | None = HTML(string=html, base_url=base_url).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"inline; filename=fluxo_geral_{fluxo.mes_ano}.pdf"
        return response
    except Exception as e:
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for("fluxos.index"))


@bp.route("/fechar", methods=["POST"])
@login_required
def fechar_fluxo():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("fluxos.index"))

    fluxo = _get_or_create_fluxo(date.today())
    if fluxo.status == "fechado":
        flash("Fluxo já está fechado.", "warning")
        return redirect(url_for("fluxos.index"))

    if not WEASYPRINT_AVAILABLE:
        flash("WeasyPrint não está disponível.", "danger")
        return redirect(url_for("fluxos.index"))

    try:
        colaboradores = CentralColaborador.query.order_by(CentralColaborador.nome.asc()).all()
        summaries = _summaries(fluxo, colaboradores)
        historicos = {c.id: _group_history(fluxo, c.id) for c in colaboradores}

        total_horas = sum(s["total_horas"] for s in summaries.values())
        total_dias = sum(s["dias_completos"] for s in summaries.values())
        total_descontos = sum(s["horas_utilizadas"] for s in summaries.values())
        total_restante = sum(s["restante"] for s in summaries.values())
        total_valor = sum(s["valor_receber"] for s in summaries.values())

        import sys

        base_dir: Any | str = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        logo_header_path: str = os.path.join(base_dir, "static", "icons", "logo black.png")
        if os.path.exists(logo_header_path):
            logo_header: str = os.path.relpath(logo_header_path, base_dir).replace("\\", "/")
        else:
            logo_header = ""

        html = render_template(
            "fluxos/pdf_geral.html",
            fluxo=fluxo,
            colaboradores=colaboradores,
            summaries=summaries,
            historicos=historicos,
            total_horas=total_horas,
            total_dias=total_dias,
            total_descontos=total_descontos,
            total_restante=total_restante,
            total_valor=total_valor,
            nome_empresa="MultiMax",
            valor_diaria=float(fluxo.valor_diaria or 0),
            logo_header=logo_header,
            logo_footer=logo_header,
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        base_url: str = str(base_dir) if base_dir else os.getcwd()
        assert HTML is not None
        pdf: bytes | None = HTML(string=html, base_url=base_url).write_pdf()

        fluxo_label = _fluxo_referencia_label(fluxo)
        fluxos_archive_dir = _get_fluxos_archive_dir("fluxos")
        pdf_path = os.path.join(fluxos_archive_dir, f"Fluxo_{fluxo_label}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf or b"")
    except Exception as e:
        flash(f"Erro ao gerar PDF geral: {e}", "danger")
        return redirect(url_for("fluxos.index"))

    storage_dir = os.path.join(os.getcwd(), "instance", "fluxos", fluxo.mes_ano)
    os.makedirs(storage_dir, exist_ok=True)

    summaries_individuais = _summaries(fluxo, colaboradores)
    for c in colaboradores:
        historicos = _group_history(fluxo, c.id)
        summary = summaries_individuais.get(c.id, {})
        html = render_template(
            "fluxos/pdf_individual.html",
            collaborator=c,
            historicos=historicos,
            fluxo=fluxo,
            summary=summary,
            logo_header="",
            data_geracao=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )
        base_url = os.getcwd()
        assert HTML is not None
        pdf = HTML(string=html, base_url=base_url).write_pdf()
        filename = f"fluxo_{fluxo.mes_ano}_{c.nome.replace(' ', '_')}.pdf"
        filepath = os.path.join(storage_dir, filename)
        with open(filepath, "wb") as f:
            f.write(pdf)
        db.session.add(FluxoArquivo(fluxo_id=fluxo.id, collaborator_id=c.id, arquivo_path=filepath))

    fluxo.status = "fechado"
    fluxo.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    db.session.commit()

    # iniciar novo fluxo
    next_month = (fluxo.data_fim + timedelta(days=1)).replace(day=1)
    _get_or_create_fluxo(next_month)

    flash("Fluxo fechado e novo fluxo iniciado.", "success")
    return redirect(url_for("fluxos.index"))
