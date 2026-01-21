import os
import shutil
import sys
import threading
import time
from typing import cast

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(session_options={"expire_on_commit": False})
login_manager = LoginManager()


def _load_env(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass


def _normalize_db_uri(uri: str | None) -> str | None:
    try:
        s = uri or ""
        if s and s.startswith("postgresql://"):
            s = "postgresql+psycopg://" + s.split("://", 1)[1]
        if s and s.startswith("postgres://"):
            s = "postgresql+psycopg://" + s.split("://", 1)[1]
        if s and (".supabase.co" in s) and ("@" in s):
            pre, post = s.split("@", 1)
            rest = post.split("/", 1)[1] if "/" in post else ""
            hostport = "aws-1-sa-east-1.pooler.supabase.com:5432"
            s = pre + "@" + hostport + ("/" + rest if rest else "")
        if s and s.startswith("postgresql+psycopg://"):
            if "sslmode=" not in s:
                s = s + ("&sslmode=require" if "?" in s else "?sslmode=require")
            if "connect_timeout=" not in s:
                s = s + ("&connect_timeout=3" if "?" in s else "?connect_timeout=3")
        return s or uri
    except Exception:
        return uri


def _extract_driver_host(uri: str | None) -> tuple[str | None, str | None]:
    try:
        if not uri or "://" not in uri:
            return None, None
        driver = uri.split("://", 1)[0]
        after = uri.split("://", 1)[1]
        hostpart = after.split("@", 1)[1] if "@" in after else after
        host = hostpart.split("/", 1)[0]
        return driver, host
    except Exception:
        return None, None


def _get_db_path() -> str:
    """Retorna o caminho do banco de dados SQLite."""
    db_file_path_env = os.getenv("DB_FILE_PATH")
    if db_file_path_env:
        return os.path.abspath(db_file_path_env).replace("\\", "/")
    if os.path.exists("/multimax-data"):
        return "/multimax-data/estoque.db"
    return "/opt/multimax-data/estoque.db"


def _get_data_dir(db_dir: str) -> str:
    """Retorna o diretório de dados para backups."""
    data_dir: str | None = os.getenv("DATA_DIR") or os.getenv("MULTIMAX_DATA_DIR") or None
    if data_dir:
        return data_dir
    if db_dir:
        return db_dir
    if os.path.exists("/multimax-data"):
        return "/multimax-data"
    return "/opt/multimax-data"


def _configure_app_database(app: Flask, db_path: str, data_dir_str: str) -> None:
    """Configura o banco de dados e diretórios no app."""
    uri_env = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    uri_env = _normalize_db_uri(uri_env)
    selected_uri = uri_env if uri_env else ("sqlite:///" + db_path)
    app.config["SQLALCHEMY_DATABASE_URI"] = selected_uri
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "uma_chave_secreta_muito_forte_e_aleatoria")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if (os.getenv("TESTING") or "").strip().lower() == "true":
        app.config["SQLALCHEMY_SESSION_OPTIONS"] = {"expire_on_commit": False}
    app.config["PER_PAGE"] = 10
    app.config["DATA_DIR"] = data_dir_str
    backup_dir = os.path.join(data_dir_str, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    app.config["BACKUP_DIR"] = backup_dir
    if isinstance(selected_uri, str) and selected_uri.startswith("sqlite:"):
        try:
            p = selected_uri.split("sqlite:///", 1)[1]
            if "?" in p:
                p = p.split("?", 1)[0]
            app.config["DB_FILE_PATH"] = p
        except Exception:
            app.config["DB_FILE_PATH"] = db_path


def _register_blueprints(app: Flask) -> tuple[bool, None]:
    """Registra todos os blueprints no app. Retorna (notif_enabled, None)."""
    from flask import Blueprint

    from .routes.api import bp as api_bp
    from .routes.auth import bp as auth_bp
    from .routes.carnes import bp as carnes_bp
    from .routes.ciclos import bp as ciclos_bp
    from .routes.colaboradores import bp as colaboradores_bp
    from .routes.cronograma import bp as cronograma_bp
    from .routes.estoque_producao import bp as estoque_producao_bp
    from .routes.exportacao import bp as exportacao_bp
    from .routes.home import bp as home_bp
    from .routes.receitas import bp as receitas_bp
    from .routes.usuarios import bp as usuarios_bp

    notif_enabled = (os.getenv("NOTIFICACOES_ENABLED", "false") or "false").lower() == "true"
    notificacoes_bp: Blueprint | None = None
    if notif_enabled:
        try:
            from .routes.notificacoes import bp as _notifs

            notificacoes_bp = _notifs
        except Exception:
            notificacoes_bp = None

    dbadmin_bp: Blueprint | None = None
    try:
        from .routes.dbadmin import bp as _dbadmin

        dbadmin_bp = _dbadmin
        app.logger.info(f"Blueprint dbadmin importado com sucesso. URL prefix: {dbadmin_bp.url_prefix}")
    except Exception as e:
        app.logger.error(f"Erro ao importar blueprint dbadmin: {e}", exc_info=True)
        dbadmin_bp = None

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(estoque_producao_bp)
    app.register_blueprint(cronograma_bp)
    app.register_blueprint(exportacao_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carnes_bp)
    app.register_blueprint(colaboradores_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ciclos_bp)
    if notificacoes_bp:
        app.register_blueprint(notificacoes_bp)
    if dbadmin_bp:
        app.register_blueprint(dbadmin_bp)
        rotas = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("dbadmin.")]
        app.logger.info(f"Blueprint dbadmin registrado com sucesso. Rotas disponíveis: {rotas}")
    else:
        app.logger.warning("Blueprint dbadmin não foi registrado (dbadmin_bp é None)")

    return notif_enabled, None


def _create_flask_app(base_dir: str) -> Flask:
    """Cria e configura a instância do Flask."""
    return Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )


def _setup_directories(db_path: str) -> str:
    """Configura e cria diretórios necessários."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    data_dir_str = _get_data_dir(db_dir)
    os.makedirs(data_dir_str, exist_ok=True)
    return data_dir_str


def _setup_login_manager(app: Flask) -> None:
    """Configura o LoginManager."""
    from .models import User

    login_manager.init_app(app)
    setattr(login_manager, "login_view", "auth.login")
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            return None


def _get_version_from_git() -> str:
    """Obtém versão do git."""
    try:
        import subprocess

        base_dir = os.path.dirname(os.path.dirname(__file__))
        r = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], cwd=base_dir, capture_output=True, text=True, timeout=2
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    except Exception:
        pass
    return ""


def _setup_extensions(app: Flask) -> None:
    """Configura extensões da aplicação."""
    db.init_app(app)
    _setup_login_manager(app)


def _setup_context_processors(app: Flask) -> None:
    """Configura context processors da aplicação."""

    @app.context_processor
    def _inject_version():
        ver = (os.getenv("APP_VERSION") or "").strip()
        if not ver:
            ver = _get_version_from_git()
        if not ver:
            try:
                from .models import AppSetting

                s = AppSetting.query.filter_by(key="app_version").first()
                ver = (s.value or "").strip() if s else ""
            except Exception as e:
                app.logger.warning(f"Erro ao obter versão do banco: {e}")
                ver = ""
        return {"git_version": ver or "dev"}


def _create_format_date_filter(app: Flask) -> None:
    """Cria e registra o filtro de formatação de data."""

    @app.template_filter("format_date_br")
    def format_date_br(date_str):
        """Formata data ISO para formato brasileiro DD/MM/YYYY"""
        if not date_str:
            return ""
        try:
            from datetime import datetime

            if isinstance(date_str, str):
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%d/%m/%Y")
            return date_str
        except Exception:
            return date_str


def _setup_template_filters(app: Flask) -> None:
    """Configura filtros de template da aplicação."""
    _create_format_date_filter(app)


def _setup_main_routes(app: Flask) -> None:
    """Configura rotas principais da aplicação."""
    from flask import jsonify, redirect, url_for
    from flask_login import current_user

    @app.route("/", strict_slashes=False)
    def _root_redirect():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return redirect(url_for("usuarios.perfil"))

    @app.route("/health", strict_slashes=False)
    def _health():
        return "ok", 200

    @app.route("/dbstatus", strict_slashes=False)
    def _dbstatus():
        try:
            from .models import User

            user_count = User.query.count()
            return jsonify({"database": "connected", "users": user_count})
        except Exception as e:
            return jsonify({"database": "error", "message": str(e)}), 500


def create_app():
    """Função principal de criação da aplicação Flask."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    _load_env(os.path.join(base_dir, ".env.txt"))

    app = _create_flask_app(base_dir)

    db_path = _get_db_path()
    data_dir_str = _setup_directories(db_path)

    _configure_app_database(app, db_path, data_dir_str)

    _setup_extensions(app)
    _register_blueprints(app)
    _setup_context_processors(app)
    _setup_template_filters(app)
    _setup_main_routes(app)

    with app.app_context():
        try:
            db.create_all()
            app.config["DB_OK"] = True
        except Exception as e:
            app.logger.error(f"Erro ao criar tabelas: {e}", exc_info=True)
            app.config["DB_OK"] = False

    return app
