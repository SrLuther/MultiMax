import os
from typing import Tuple, cast
from urllib.parse import urlparse

import requests

from .. import db
from ..models import AppSetting, SystemLog

AUTO_SETTING_KEY = "whatsapp_auto_notifications_enabled"
DEFAULT_AUTO_ENV = (os.getenv("NOTIFICACOES_ENABLED", "false") or "false").strip().lower() == "true"


def _log_system(event: str, details: str, actor: str | None = None) -> None:
    """Registra ação no SystemLog sem quebrar o fluxo em caso de erro."""
    try:
        log = SystemLog()
        log.origem = "whatsapp"
        log.evento = event
        log.detalhes = (details or "")[:255]
        log.usuario = actor
        db.session.add(log)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _get_setting(create_if_missing: bool = True) -> AppSetting | None:
    try:
        setting = cast(AppSetting | None, AppSetting.query.filter_by(key=AUTO_SETTING_KEY).first())
        if not setting and create_if_missing:
            setting = AppSetting()
            setting.key = AUTO_SETTING_KEY
            setting.value = "true" if DEFAULT_AUTO_ENV else "false"
            db.session.add(setting)
            db.session.commit()
        return setting
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def get_auto_notifications_enabled() -> bool:
    setting = _get_setting(create_if_missing=True)
    if setting and isinstance(setting.value, str):
        return setting.value.strip().lower() == "true"
    return DEFAULT_AUTO_ENV


def set_auto_notifications_enabled(enabled: bool, actor: str | None = None) -> None:
    setting = _get_setting(create_if_missing=True)
    if not setting:
        return
    try:
        setting.value = "true" if enabled else "false"
        db.session.commit()
        state_label = "ativadas" if enabled else "desativadas"
        _log_system("auto_toggle", f"Notificações automáticas {state_label}", actor)
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _notify_url() -> str:
    return (os.getenv("WHATSAPP_NOTIFY_URL") or "https://www.multimax.tec.br/notify").strip()


def _candidate_urls(primary: str) -> list[str]:
    """Retorna URLs candidatas para o gateway de WhatsApp.

    Ordem de tentativa:
    1. URL primária configurada
    2. Fallback local: 127.0.0.1
    3. Fallback local: localhost
    """
    fallbacks = [
        "http://127.0.0.1:3001/notify",
        "http://localhost:3001/notify",
    ]
    urls: list[str] = []
    if primary:
        urls.append(primary)
    for fb in fallbacks:
        if fb not in urls:
            urls.append(fb)
    return urls


def get_gateway_display_url() -> str:
    url = _notify_url()
    if not url:
        return "não configurado"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path or url
        path = parsed.path or ""
        base = f"{parsed.scheme}://{netloc}{path}" if parsed.scheme else url
        return base
    except Exception:
        return url


def _timeout_seconds() -> float:
    try:
        return float(os.getenv("WHATSAPP_NOTIFY_TIMEOUT", "8"))
    except (TypeError, ValueError):
        return 8.0


def send_whatsapp_message(message: str, actor: str | None = None, origin: str = "manual") -> Tuple[bool, str]:
    msg = (message or "").strip()
    if not msg:
        return False, "Mensagem vazia."

    url = _notify_url()
    if not url:
        return False, "Endpoint do serviço WhatsApp não configurado."

    payload = {"mensagem": msg, "origin": origin}
    headers = {"Content-Type": "application/json"}
    last_error: str = ""
    for candidate in _candidate_urls(url):
        try:
            resp = requests.post(
                candidate, json=payload, headers=headers, timeout=_timeout_seconds()
            )  # nosec B113: timeout definido explicitamente
            if resp.status_code >= 400:
                snippet = (resp.text or "").strip().replace("\n", " ")[:200]
                last_error = f"Erro do serviço ({resp.status_code}): {snippet or 'resposta vazia'}"
                continue
            # sucesso
            _log_system("manual_send", f"Mensagem enviada via gateway ({len(msg)} chars)", actor)
            return True, ""
        except requests.RequestException as exc:
            last_error = f"Falha ao contatar serviço WhatsApp: {exc}"
            continue

    if last_error:
        return False, last_error
    return False, "Falha ao contatar serviço WhatsApp: erro desconhecido"
