import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .. import db
from ..models import Collaborator, SystemLog, User, UserLogin
from ..password_hash import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)


def _validate_registration_data(username, password, confirm_password):
    """Valida dados de cadastro e retorna (válido, mensagem_erro)."""
    if not username or len(username) < 3:
        return False, "O nome de usuário deve ter pelo menos 3 caracteres."

    if not password or len(password) < 4:
        return False, "A senha deve ter pelo menos 4 caracteres."

    if password != confirm_password:
        return False, "As senhas não coincidem."

    if User.query.filter_by(username=username).first():
        return False, "Este nome de usuário já está em uso."

    return True, None


def _create_user_and_collaborator(username, password, name):
    """Cria novo usuário e collaborator associado."""
    try:
        new_user = User()
        new_user.username = username
        new_user.name = name[:100]
        new_user.password_hash = generate_password_hash(password)
        new_user.nivel = "visualizador"

        db.session.add(new_user)
        db.session.flush()

        # Criar Collaborator automaticamente
        try:
            new_collaborator = Collaborator()
            new_collaborator.name = name[:100]
            new_collaborator.user_id = new_user.id
            new_collaborator.active = True
            db.session.add(new_collaborator)
        except Exception as collab_e:
            logger.warning(f"Erro ao criar Collaborator para novo usuário {username}: {collab_e}")

        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao cadastrar usuário: {e}", exc_info=True)
        return False, "Erro ao realizar cadastro. Tente novamente."


def _handle_registration():
    """Processa cadastro de novo usuário."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    name = request.form.get("name", "").strip() or username

    # Validar dados
    valid, error_msg = _validate_registration_data(username, password, confirm_password)
    if not valid:
        flash(error_msg, "danger")
        return render_template("login.html", show_register=True)

    # Criar usuário
    success, error_msg = _create_user_and_collaborator(username, password, name)
    if not success:
        flash(error_msg, "danger")
        return render_template("login.html", show_register=True)

    flash("Cadastro realizado com sucesso! Faça login para continuar.", "success")
    return render_template("login.html", show_register=False)


def _get_client_info():
    """Extrai informações do cliente (IP e User-Agent)."""
    try:
        ip = request.remote_addr or request.environ.get("HTTP_X_FORWARDED_FOR") or ""
    except (AttributeError, KeyError):
        ip = ""

    try:
        ua = request.headers.get("User-Agent", "")
    except (AttributeError, KeyError):
        ua = ""

    return ip[:255] if ip else "", ua[:500] if ua else ""


def _log_user_login(user):
    """Registra login do usuário no sistema."""
    try:
        log = SystemLog()
        log.origem = "Acesso"
        log.evento = "login"
        log.detalhes = "Acesso ao sistema"
        log.usuario = user.name
        db.session.add(log)

        # Registrar histórico de login
        ip, ua = _get_client_info()
        try:
            ul = UserLogin()
            ul.user_id = user.id
            ul.username = user.username
            ul.ip_address = ip
            ul.user_agent = ua
            db.session.add(ul)
        except Exception as e:
            logger.warning(f"Erro ao registrar login: {e}")

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar log de login: {e}")


def _handle_login():
    """Processa login de usuário existente."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        _log_user_login(user)
        flash("Login realizado com sucesso!", "success")
        return redirect(url_for("usuarios.perfil"))
    else:
        flash("Nome de usuário ou senha inválidos.", "danger")
        return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("usuarios.perfil"))

    if request.method == "POST":
        action = request.form.get("action", "login")

        if action == "register":
            return _handle_registration()
        else:
            result = _handle_login()
            if result:
                return result

    show_register = request.args.get("register", "").lower() == "true"
    return render_template("login.html", show_register=show_register)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("usuarios.perfil"))
    return redirect(url_for("auth.login", register="true"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("auth.login"))
