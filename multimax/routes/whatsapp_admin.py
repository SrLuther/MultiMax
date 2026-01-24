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
        base_dir = os.path.dirname(current_app.root_path)
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
    if not auth_header or not token:
        return False
    header = auth_header.strip()
    if not header.lower().startswith("bearer "):
        return False
    provided = header.split(" ", 1)[1].strip()
    if not provided or provided != token:
        return False
    ip = (remote_ip or "").strip()
    return ip in ("127.0.0.1", "::1")


@bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
def painel():
    _require_dev()
    auto_enabled = get_auto_notifications_enabled()
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
    bearer_ok = _is_local_service_call(request.headers.get("Authorization", ""), request.remote_addr or "", token)

    if not bearer_ok:
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


@bp.route("/auto", methods=["POST"], strict_slashes=False)
@login_required
def toggle_auto():
    _require_dev()
    desired_state = (request.form.get("auto_enabled") or "").lower() == "on"
    set_auto_notifications_enabled(desired_state, actor=current_user.username)
    if desired_state:
        flash("Notificações automáticas foram ativadas.", "success")
    else:
        flash("Notificações automáticas foram desativadas. Envio manual continua disponível.", "info")
    return redirect(url_for("whatsapp_admin.painel"))
