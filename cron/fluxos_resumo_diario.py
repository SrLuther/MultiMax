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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multimax import create_app  # noqa: E402
from multimax.services.fluxos_resumo_diario import enviar_resumo_diario_fluxos  # noqa: E402


def main() -> None:
    app = create_app()

    with app.app_context():
        ok, info = enviar_resumo_diario_fluxos(origin="fluxos_resumo_diario")
        if not ok:
            print(f"[ERRO] {info}")


if __name__ == "__main__":
    main()
