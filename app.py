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
    app.config['_startup_time'] = time.time()  # Registrar tempo de inicialização
    logger.info("Aplicação Flask criada com sucesso")

    # Expor função perform_backup no app, se disponível
    try:
        from multimax import _perform_backup as __perform_backup

        def perform_backup(retain_count: int = 20, force: bool = False, daily: bool = False) -> bool:
            return bool(__perform_backup(app, retain_count=retain_count, force=force, daily=daily))

        setattr(app, "perform_backup", perform_backup)
        logger.info("Função perform_backup registrada no app")
    except Exception as e:
        logger.warning(f"Não foi possível registrar perform_backup: {e}")
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


def _start_backup_scheduler():  # noqa: C901
    enabled = os.getenv("BACKUP_SCHEDULER_ENABLED", "true").lower() == "true"
    if not enabled:
        return

    daily_enabled = os.getenv("BACKUP_DAILY_ENABLED", "true").lower() == "true"
    weekly_enabled = os.getenv("BACKUP_WEEKLY_ENABLED", "true").lower() == "true"

    def _seconds_until(hour: int, minute: int) -> int:
        import datetime as _dt

        now = _dt.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + _dt.timedelta(days=1)
        return int((target - now).total_seconds())

    def _seconds_until_weekly(weekday: int, hour: int, minute: int) -> int:
        import datetime as _dt

        now = _dt.datetime.now()
        days_ahead = (weekday - now.weekday()) % 7
        target_day = now + _dt.timedelta(days=days_ahead)
        target = target_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + _dt.timedelta(days=7)
        return int((target - now).total_seconds())

    def _loop():
        while True:
            try:
                # Daily at 00:05
                if daily_enabled:
                    delay = _seconds_until(0, 5)
                    time.sleep(max(5, delay))
                    ok = False
                    # Preferir função interna estável
                    try:
                        from multimax import _perform_backup as __perform_backup

                        ok = bool(__perform_backup(app, retain_count=20, daily=True))
                    except Exception:
                        pass
                    # Fallback ao atributo se disponível
                    if not ok:
                        fn = getattr(app, "perform_backup", None)
                        if callable(fn):
                            ok = bool(fn(retain_count=20, daily=True))
                    logger.info(f"Backup diário executado: {'OK' if ok else 'FAIL'}")

                # Weekly on Sunday 02:00
                if weekly_enabled:
                    delay = _seconds_until_weekly(6, 2, 0)  # 6 = Sunday
                    time.sleep(max(5, delay))
                    ok = False
                    try:
                        from multimax import _perform_backup as __perform_backup

                        ok = bool(__perform_backup(app, retain_count=20, daily=False))
                    except Exception:
                        pass
                    if not ok:
                        fn = getattr(app, "perform_backup", None)
                        if callable(fn):
                            ok = bool(fn(retain_count=20, daily=False))
                    logger.info(f"Backup semanal executado: {'OK' if ok else 'FAIL'}")
            except Exception as e:
                logger.error(f"Erro no agendador de backup: {e}")
                time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True, name="backup-scheduler")
    t.start()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    _start_keepalive()
    _start_backup_scheduler()
    try:
        from waitress import serve  # type: ignore
    except ImportError:
        serve = None
    if serve:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=debug)
