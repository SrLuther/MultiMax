from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_

from ..models import CentralColaborador, FluxoLancamento, SystemLog, db
from ..routes.fluxos import _get_or_create_fluxo, _summaries
from ..services.whatsapp_gateway import send_whatsapp_message

SETOR_TITULO = "Açougue"


def _log_system(event: str, details: str, origin: str) -> None:
    try:
        log = SystemLog()
        log.origem = origin
        log.evento = event
        log.detalhes = (details or "")[:255]
        log.usuario = "sistema"
        db.session.add(log)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _month_name(ref_date: date) -> str:
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
    return meses[ref_date.month - 1]


def _fluxo_colaboradores_setor() -> list[CentralColaborador]:
    setor_filter = or_(
        CentralColaborador.setor.ilike("%açougue%"),
        CentralColaborador.setor.ilike("%acougue%"),
    )
    return (
        CentralColaborador.query.filter(CentralColaborador.ativo.is_(True), setor_filter)
        .order_by(CentralColaborador.nome.asc())
        .all()
    )


def _latest_lancamento_date(collab_ids: list[int]) -> date | None:
    if not collab_ids:
        return None
    ultimo = (
        FluxoLancamento.query.filter(FluxoLancamento.collaborator_id.in_(collab_ids))
        .order_by(FluxoLancamento.data.desc(), FluxoLancamento.id.desc())
        .first()
    )
    if ultimo and ultimo.data:
        return ultimo.data
    return None


def _latest_lancamento_date_fluxo(fluxo_id: int, collab_ids: list[int]) -> date | None:
    if not collab_ids:
        return None
    ultimo = (
        FluxoLancamento.query.filter(
            FluxoLancamento.fluxo_id == fluxo_id,
            FluxoLancamento.collaborator_id.in_(collab_ids),
        )
        .order_by(FluxoLancamento.data.desc(), FluxoLancamento.id.desc())
        .first()
    )
    if ultimo and ultimo.data:
        return ultimo.data
    return None


def enviar_resumo_geral_fluxos(
    *,
    now: datetime | None = None,
    origin: str = "fluxos_resumo_geral",
    actor: str = "sistema",
) -> tuple[bool, str]:
    now = now or datetime.now(ZoneInfo("America/Sao_Paulo"))

    colaboradores = _fluxo_colaboradores_setor()
    if not colaboradores:
        return False, "Nenhum colaborador ativo encontrado para o setor."

    collab_ids = [c.id for c in colaboradores]
    ultimo_registro = _latest_lancamento_date(collab_ids)
    ref_date = ultimo_registro or now.date()

    fluxo = _get_or_create_fluxo(ref_date)
    summaries = _summaries(fluxo, colaboradores)

    atualizado_em = _latest_lancamento_date_fluxo(fluxo.id, collab_ids) or ref_date

    linhas = [
        "*RESUMO GERAL*",
        f"*Fluxo atual:* {_month_name(fluxo.data_inicio or ref_date)}",
        "--------------------------------",
    ]

    for colab in colaboradores:
        s = summaries.get(colab.id)
        if not s:
            continue
        linhas.append(f"*{colab.nome}*")
        linhas.append(f"- H Bruto: {s['total_horas']:.1f}h")
        linhas.append(f"- H Descontos: {s['horas_utilizadas']:.1f}h")
        linhas.append(f"- H Líquido: {s['restante']:.1f}h")
        linhas.append(f"- Dias completos: {s['dias_completos']}")
        linhas.append(f"- R$ estimado: R$ {s['valor_receber']:.2f}")
        linhas.append("--------------------------------")

    linhas.append(f"*Atualizado em:* {atualizado_em.strftime('%d/%m/%Y')}")

    mensagem = "\n".join(linhas).strip()

    sucesso, erro = send_whatsapp_message(
        message=mensagem,
        actor=actor,
        origin=origin,
    )
    if sucesso:
        _log_system("envio_resumo_geral", f"Resumo geral enviado ({SETOR_TITULO})", origin)
        return True, "Resumo geral enviado com sucesso."

    _log_system("envio_falha", f"Falha ao enviar resumo geral: {erro}", origin)
    return False, erro or "Falha ao enviar resumo geral"
