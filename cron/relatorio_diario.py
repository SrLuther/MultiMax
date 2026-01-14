import os

from multimax import create_app
from multimax.services.notificacao_service import enviar_relatorio_diario


def main():
    app = create_app()
    if (os.getenv("NOTIFICACOES_ENABLED", "false") or "false").lower() != "true":
        return
    hora = os.getenv("NOTIFICACOES_ENVIO_AUTOMATICO_HORA", "20").strip()
    with app.app_context():
        enviar_relatorio_diario("automatico", False)


if __name__ == "__main__":
    main()
