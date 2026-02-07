#!/usr/bin/env python3
r"""
Resumo diário do Fluxos (Açougue) via WhatsApp.
Executa todos os dias às 20h (Brasília).

Configuração no crontab:
    0 20 * * * cd /opt/multimax && docker-compose exec -T multimax /app/.venv/bin/python3 \
        /app/cron/fluxos_resumo_diario.py >> /var/log/multimax/cron_fluxos_resumo.log 2>&1
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multimax import create_app, db  # noqa: E402
from multimax.models import CentralColaborador, CentralVacation, FluxoConfig, FluxoLancamento, SystemLog  # noqa: E402
from multimax.services.whatsapp_gateway import send_whatsapp_message  # noqa: E402

SETOR_TITULO = "Açougue"


def log_system(event: str, details: str) -> None:
    try:
        log = SystemLog()
        log.origem = "cron_fluxos_resumo"
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


def _start_end_today(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def main() -> None:
    app = create_app()

    with app.app_context():
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        start, end = _start_end_today(now)

        setor_filter = or_(
            CentralColaborador.setor.ilike("%açougue%"),
            CentralColaborador.setor.ilike("%acougue%"),
        )
        colaboradores = (
            CentralColaborador.query.filter(CentralColaborador.ativo.is_(True), setor_filter)
            .order_by(CentralColaborador.nome.asc())
            .all()
        )

        collab_map = {c.id: c for c in colaboradores}
        collab_ids = list(collab_map.keys())

        # Férias registradas hoje
        ferias = []
        if collab_ids:
            ferias = (
                CentralVacation.query.filter(
                    CentralVacation.collaborator_id.in_(collab_ids),
                    CentralVacation.criado_em >= start,
                    CentralVacation.criado_em < end,
                )
                .order_by(CentralVacation.criado_em.asc())
                .all()
            )

        # Mudança no valor da diária
        valor_diaria_msg = None
        config = FluxoConfig.query.first()
        if config and config.updated_at and start <= config.updated_at < end:
            valor_diaria_msg = f"💰 Valor da diária atualizado hoje: R$ {float(config.valor_diaria):.2f}"

        # Lançamentos do dia (criados ou alterados hoje)
        lancamentos = []
        if collab_ids:
            lancamentos = (
                FluxoLancamento.query.filter(
                    FluxoLancamento.collaborator_id.in_(collab_ids),
                    or_(
                        FluxoLancamento.created_at.between(start, end),
                        FluxoLancamento.updated_at.between(start, end),
                    ),
                )
                .order_by(FluxoLancamento.data.asc(), FluxoLancamento.id.asc())
                .all()
            )

        if not ferias and not valor_diaria_msg and not lancamentos:
            mensagem = "Sem novos lançamentos registrados até o momento"
            sucesso, erro = send_whatsapp_message(
                message=mensagem,
                actor="sistema",
                origin="fluxos_resumo_diario",
            )
            if sucesso:
                log_system("envio_sem_novidades", "Resumo diário enviado sem alterações")
            else:
                log_system("envio_falha", f"Falha ao enviar resumo: {erro}")
            return

        linhas = [
            f"📌 Fluxos — Resumo diário ({SETOR_TITULO})",
            f"Data: {now.strftime('%d/%m/%Y')}",
            "",
        ]

        if valor_diaria_msg:
            linhas.append(valor_diaria_msg)
            linhas.append("")

        if ferias:
            linhas.append("🏖️ Férias registradas hoje:")
            for f in ferias:
                colab = collab_map.get(f.collaborator_id)
                nome = colab.nome if colab else f"ID {f.collaborator_id}"
                dias = (f.data_fim - f.data_inicio).days + 1
                linhas.append(
                    f"• {nome}: {f.data_inicio.strftime('%d/%m')} a {f.data_fim.strftime('%d/%m')} ({dias} dias)"
                )
            linhas.append("")

        if lancamentos:
            linhas.append("⏱️ Lançamentos do dia:")
            lanc_por_colab: dict[int, list[FluxoLancamento]] = {}
            for lanc in lancamentos:
                lanc_por_colab.setdefault(lanc.collaborator_id, []).append(lanc)

            for collab_id, itens in lanc_por_colab.items():
                colab = collab_map.get(collab_id)
                nome = colab.nome if colab else f"ID {collab_id}"
                linhas.append(f"• {nome}")
                for lanc in itens:
                    horas = f"{lanc.horas:+g}h" if lanc.horas is not None else "0h"
                    obs = f" — {lanc.observacao}" if lanc.observacao else ""
                    linhas.append(f"  - {lanc.data.strftime('%d/%m')}: {horas} ({lanc.descricao}){obs}")
            linhas.append("")

        mensagem = "\n".join([line for line in linhas if line is not None]).strip()

        sucesso, erro = send_whatsapp_message(
            message=mensagem,
            actor="sistema",
            origin="fluxos_resumo_diario",
        )
        if sucesso:
            log_system("envio_resumo", f"Resumo diário enviado ({SETOR_TITULO})")
        else:
            log_system("envio_falha", f"Falha ao enviar resumo: {erro}")


if __name__ == "__main__":
    main()
