import os

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..services.whatsapp_gateway import (
    get_auto_notifications_enabled,
    get_gateway_display_url,
    send_whatsapp_message,
    set_auto_notifications_enabled,
)

bp = Blueprint("whatsapp_admin", __name__, url_prefix="/dev/whatsapp")


def _require_dev():
    if not current_user.is_authenticated or current_user.nivel != "DEV":
        abort(403)


def _load_service_token() -> str:
    token_env = (os.getenv("WHATSAPP_SERVICE_TOKEN") or "").strip()
    if token_env:
        return token_env
    # Fallback: tentar ler token de .env.txt sem reiniciar
    try:
        # Priorizar root_path da aplicação
        candidates = [current_app.root_path]
        # Também considerar diretório pai por compatibilidade com alguns setups
        parent_dir = os.path.dirname(current_app.root_path)
        if parent_dir and parent_dir not in candidates:
            candidates.append(parent_dir)
        for base_dir in candidates:
            env_path = os.path.join(base_dir, ".env.txt")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k.strip() == "WHATSAPP_SERVICE_TOKEN":
                            return v.strip()
    except Exception:
        pass
    return ""


def _is_local_service_call(auth_header: str, remote_ip: str, token: str) -> bool:
    """Valida chamada de serviço via token Bearer. Token é suficiente para autorizar."""
    if not auth_header or not token:
        return False
    header = auth_header.strip()
    if not header.lower().startswith("bearer "):
        return False
    provided = header.split(" ", 1)[1].strip()
    # Se token bater, autorizar (token já é a camada de segurança)
    return provided == token


def _extract_provided_token(req) -> str:
    """Extrai o token fornecido pela chamada do serviço.

    Aceita:
    - Header Authorization: Bearer <token>
    - Header X-Service-Token / X-WhatsApp-Service-Token
    - Campo de formulário 'token' (fallback)
    """
    auth = (req.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    # Headers alternativos para compatibilidade
    alt = (req.headers.get("X-Service-Token") or req.headers.get("X-WhatsApp-Service-Token") or "").strip()
    if alt:
        return alt
    # Fallback em form
    form_token = (req.form.get("token") or "").strip()
    if form_token:
        return form_token
    return ""


@bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
def painel():
    _require_dev()
    print(
        f"[DEBUG] Painel WhatsApp acessado por: "
        f"{getattr(current_user, 'username', None)} "
        f"(nivel={getattr(current_user, 'nivel', None)})"
    )
    auto_enabled = get_auto_notifications_enabled()
    print(f"[DEBUG] Estado atual do Bloco B (auto_enabled): {auto_enabled}")
    gateway_url = get_gateway_display_url()
    return render_template(
        "whatsapp_admin.html",
        active_page="whatsapp_admin",
        auto_enabled=auto_enabled,
        gateway_url=gateway_url,
    )


@bp.route("/enviar", methods=["POST"], strict_slashes=False)
def enviar():
    token = _load_service_token()
    provided = _extract_provided_token(request)
    bearer_ok = bool(token) and bool(provided) and provided == token

    if not bearer_ok:
        # Se um header/token foi enviado mas inválido, responder em JSON 403 para serviço
        if provided:
            return jsonify({"ok": False, "error": "token inválido"}), 403
        # Fluxo web tradicional: exigir login DEV
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        _require_dev()

    message = (request.form.get("message") or "").strip()
    if not message:
        if bearer_ok:
            return jsonify({"ok": False, "error": "mensagem vazia"}), 400
        flash("Digite uma mensagem para enviar.", "warning")
        return redirect(url_for("whatsapp_admin.painel"))

    actor = current_user.username if current_user.is_authenticated else "service-token"
    origin = "manual-dev" if current_user.is_authenticated else "service"
    ok, error = send_whatsapp_message(message, actor=actor, origin=origin)
    if bearer_ok:
        status = 200 if ok else 502
        return jsonify({"ok": ok, "error": error or None}), status
    if ok:
        flash("Mensagem enviada ao serviço de WhatsApp.", "success")
    else:
        flash(f"Falha ao enviar mensagem: {error}", "danger")
    return redirect(url_for("whatsapp_admin.painel"))


@bp.route("/auto/toggle", methods=["POST"], strict_slashes=False)
@login_required
def toggle_auto_rest():
    _require_dev()
    # Aceita JSON ou form
    if request.is_json:
        data = request.get_json(silent=True) or {}
        desired_state = bool(data.get("enabled"))
    else:
        desired_state = (request.form.get("auto_enabled") or "").lower() == "on"
    try:
        set_auto_notifications_enabled(desired_state, actor=current_user.username)
        new_state = get_auto_notifications_enabled()
        msg = (
            "Notificações automáticas ativadas."
            if new_state
            else "Notificações automáticas desativadas. Envio manual continua disponível."
        )
        return jsonify({"ok": True, "enabled": new_state, "message": msg}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
