from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
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
@login_required
def enviar():
    _require_dev()
    message = (request.form.get("message") or "").strip()
    if not message:
        flash("Digite uma mensagem para enviar.", "warning")
        return redirect(url_for("whatsapp_admin.painel"))

    ok, error = send_whatsapp_message(message, actor=current_user.username, origin="manual-dev")
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
