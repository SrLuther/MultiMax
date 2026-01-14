import logging
import os
import sys
import threading
import time
import urllib.request
from urllib.error import HTTPError, URLError

from multimax import create_app

# Configurar logging antes de criar o app
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Criar app com tratamento de erros
try:
    logger.info("Iniciando criação da aplicação Flask...")
    app = create_app()
    logger.info("Aplicação Flask criada com sucesso")
except Exception as e:
    logger.critical(f"ERRO CRÍTICO ao criar aplicação Flask: {e}", exc_info=True)
    # Tentar criar app novamente com configuração mínima
    try:
        logger.warning("Tentando criar app com configuração mínima...")
        app = create_app()
        logger.info("App criado com configuração mínima")
    except Exception as e2:
        logger.critical(f"Falha total ao criar aplicação: {e2}", exc_info=True)
        sys.exit(1)


def _start_keepalive():
    enabled = os.getenv("KEEPALIVE_ENABLED", "false").lower() == "true"
    if not enabled:
        return
    url = (os.getenv("KEEPALIVE_URL") or "").strip()
    if not url:
        return
    try:
        interval = int(os.getenv("KEEPALIVE_INTERVAL", "300"))
        if interval < 60:
            interval = 300  # Mínimo de 60 segundos para evitar spam
    except (ValueError, TypeError):
        interval = 300

    def _loop():
        while True:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MultiMax-KeepAlive"})
                urllib.request.urlopen(req, timeout=10).read()
            except HTTPError as e:
                logger.warning(f"Keepalive HTTP error: {e.code} - {e.reason}")
            except URLError as e:
                logger.warning(f"Keepalive URL error: {e.reason}")
            except TimeoutError:
                logger.warning("Keepalive timeout")
            except Exception as e:
                logger.error(f"Keepalive unexpected error: {type(e).__name__}: {e}", exc_info=True)
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True, name="keepalive-thread")
    t.start()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    _start_keepalive()
    try:
        from waitress import serve
    except ImportError:
        serve = None
    if serve:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=debug)
