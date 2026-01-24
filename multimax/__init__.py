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
    """Retorna o diretÃ³rio de dados para backups."""
    data_dir: str | None = os.getenv("DATA_DIR") or os.getenv("MULTIMAX_DATA_DIR") or None
    if data_dir:
        return data_dir
    if db_dir:
        return db_dir
    if os.path.exists("/multimax-data"):
        return "/multimax-data"
    return "/opt/multimax-data"


def _configure_app_database(app: Flask, db_path: str, data_dir_str: str) -> None:
    """Configura o banco de dados e diretÃ³rios no app."""
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
    from .routes.whatsapp_admin import bp as whatsapp_admin_bp

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
    app.register_blueprint(whatsapp_admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ciclos_bp)
    if notificacoes_bp:
        app.register_blueprint(notificacoes_bp)
    if dbadmin_bp:
        app.register_blueprint(dbadmin_bp)
        rotas = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("dbadmin.")]
        app.logger.info(f"Blueprint dbadmin registrado com sucesso. Rotas disponÃ­veis: {rotas}")
    else:
        app.logger.warning("Blueprint dbadmin nÃ£o foi registrado (dbadmin_bp Ã© None)")

    return notif_enabled, None


def _create_flask_app(base_dir: str) -> Flask:
    """Cria e configura a instÃ¢ncia do Flask."""
    return Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )


def _setup_directories(db_path: str) -> str:
    """Configura e cria diretÃ³rios necessÃ¡rios."""
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
    login_manager.login_message = "Por favor, faÃ§a login para acessar esta pÃ¡gina."
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
    """ObtÃ©m versÃ£o do git."""
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
    """Configura extensÃµes da aplicaÃ§Ã£o."""
    db.init_app(app)
    _setup_login_manager(app)


def _setup_context_processors(app: Flask) -> None:
    """Configura context processors da aplicaÃ§Ã£o."""

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
                app.logger.warning(f"Erro ao obter versÃ£o do banco: {e}")
                ver = ""
        return {"git_version": ver or "dev"}


def _create_format_date_filter(app: Flask) -> None:
    """Cria e registra o filtro de formataÃ§Ã£o de data."""

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
    """Configura filtros de template da aplicaÃ§Ã£o."""
    _create_format_date_filter(app)


def _setup_main_routes(app: Flask) -> None:
    """Configura rotas principais da aplicaÃ§Ã£o."""
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
        """Diagnóstico premium do banco de dados com performance detalhada."""
        try:
            import os
            import sqlite3
            from datetime import datetime

            from .models import User

            # Dados básicos
            user_count = User.query.count()
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            db_file_path = app.config.get("DB_FILE_PATH", "")
            backup_dir = app.config.get("BACKUP_DIR", "")

            # Estatísticas do banco SQLite
            db_size_mb = 0
            page_count = 0
            page_size = 0
            table_count = 0
            is_sqlite = db_file_path and os.path.exists(db_file_path)

            if is_sqlite:
                db_size_mb = round(os.path.getsize(db_file_path) / (1024 * 1024), 2)
                try:
                    conn = sqlite3.connect(db_file_path)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    conn.close()
                except Exception:
                    pass

            # Backups detalhados
            backup_count = 0
            backup_size_mb = 0
            backup_24h = False
            recent_backups = []

            if backup_dir and os.path.exists(backup_dir):
                for fname in os.listdir(backup_dir):
                    fpath = os.path.join(backup_dir, fname)
                    if os.path.isfile(fpath):
                        fsize_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
                        backup_count += 1
                        backup_size_mb += fsize_mb
                        if fname == "backup-24h.sqlite":
                            backup_24h = True
                        mtime = os.path.getmtime(fpath)
                        recent_backups.append((fname, fsize_mb, mtime))

                backup_size_mb = round(backup_size_mb, 2)
                recent_backups.sort(key=lambda x: x[2], reverse=True)
                recent_backups = recent_backups[:5]

            # Uptime
            import time

            uptime_sec = int(time.time() - app.config.get("_startup_time", time.time()))
            uptime_min = uptime_sec // 60
            uptime_h = uptime_min // 60

            # HTML premium
            backup_list_html = ""
            for fname, size, mtime in recent_backups:
                dt = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
                backup_list_html += f'<div class="backup-item"><span class="backup-name">{fname}</span><span class="backup-meta">{size} MB • {dt}</span></div>'

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Diagnóstico Banco de Dados</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
                        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        color: #e2e8f0;
                        padding: 24px;
                        line-height: 1.6;
                    }}

                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}

                    .header {{
                        background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
                        border-radius: 12px;
                        padding: 32px;
                        margin-bottom: 24px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    }}

                    .header h1 {{
                        font-size: 28px;
                        font-weight: 700;
                        margin-bottom: 8px;
                    }}

                    .header p {{
                        opacity: 0.9;
                        font-size: 14px;
                    }}

                    .grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                        gap: 20px;
                        margin-bottom: 24px;
                    }}

                    .card {{
                        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                        border: 1px solid #334155;
                        border-radius: 12px;
                        padding: 24px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                        transition: all 0.3s ease;
                    }}

                    .card:hover {{
                        border-color: #64748b;
                        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
                    }}

                    .card-header {{
                        display: flex;
                        align-items: center;
                        margin-bottom: 16px;
                        font-size: 16px;
                        font-weight: 600;
                        color: #3b82f6;
                    }}

                    .card-icon {{
                        font-size: 20px;
                        margin-right: 10px;
                    }}

                    .stat {{
                        display: flex;
                        justify-content: space-between;
                        padding: 12px 0;
                        border-bottom: 1px solid #334155;
                        font-size: 14px;
                    }}

                    .stat:last-child {{
                        border-bottom: none;
                    }}

                    .stat-label {{
                        color: #94a3b8;
                    }}

                    .stat-value {{
                        color: #e2e8f0;
                        font-weight: 600;
                        font-family: 'Courier New', monospace;
                    }}

                    .status-ok {{ color: #10b981; }}
                    .status-warn {{ color: #f59e0b; }}
                    .status-error {{ color: #ef4444; }}

                    .progress-bar {{
                        width: 100%;
                        height: 6px;
                        background: #334155;
                        border-radius: 3px;
                        overflow: hidden;
                        margin: 8px 0;
                    }}

                    .progress-fill {{
                        height: 100%;
                        background: linear-gradient(90deg, #3b82f6, #1e40af);
                        transition: width 0.3s ease;
                    }}

                    .backup-item {{
                        background: #334155;
                        padding: 12px;
                        border-radius: 6px;
                        margin: 8px 0;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        font-size: 13px;
                    }}

                    .backup-name {{
                        font-family: 'Courier New', monospace;
                        color: #60a5fa;
                    }}

                    .backup-meta {{
                        color: #94a3b8;
                        font-size: 12px;
                    }}

                    .metrics-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                        gap: 12px;
                        margin-top: 16px;
                    }}

                    .metric {{
                        background: #334155;
                        padding: 12px;
                        border-radius: 6px;
                        text-align: center;
                    }}

                    .metric-value {{
                        font-size: 18px;
                        font-weight: 700;
                        color: #3b82f6;
                        font-family: 'Courier New', monospace;
                    }}

                    .metric-label {{
                        font-size: 11px;
                        color: #94a3b8;
                        margin-top: 4px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}

                    .status-badge {{
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                        background: rgba(16, 185, 129, 0.1);
                        color: #10b981;
                        border: 1px solid #10b981;
                    }}

                    .alert {{
                        background: rgba(239, 68, 68, 0.1);
                        border-left: 4px solid #ef4444;
                        padding: 12px;
                        border-radius: 6px;
                        margin: 12px 0;
                        font-size: 13px;
                        color: #fca5a5;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 Diagnóstico Completo</h1>
                        <p>Status e Performance do Banco de Dados • {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    </div>

                    <div class="grid">
                        <!-- Card: Status do Banco -->
                        <div class="card">
                            <div class="card-header">
                                <span class="card-icon">🗄️</span>
                                Status do Banco
                            </div>
                            <div class="stat">
                                <span class="stat-label">Estado</span>
                                <span class="stat-value status-ok">✓ Conectado</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Tipo</span>
                                <span class="stat-value">SQLite</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Usuários</span>
                                <span class="stat-value">{user_count}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Tabelas</span>
                                <span class="stat-value">{table_count}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Tamanho</span>
                                <span class="stat-value">{db_size_mb} MB</span>
                            </div>
                        </div>

                        <!-- Card: Performance -->
                        <div class="card">
                            <div class="card-header">
                                <span class="card-icon">⚡</span>
                                Performance
                            </div>
                            <div class="stat">
                                <span class="stat-label">Páginas</span>
                                <span class="stat-value">{page_count:,}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Tamanho Página</span>
                                <span class="stat-value">{page_size} bytes</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Uptime</span>
                                <span class="stat-value">{uptime_h}h {uptime_min % 60}m</span>
                            </div>
                            <div class="metrics-grid">
                                <div class="metric">
                                    <div class="metric-value">{db_size_mb}</div>
                                    <div class="metric-label">MB</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">{table_count}</div>
                                    <div class="metric-label">Tabelas</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">{user_count}</div>
                                    <div class="metric-label">Usuários</div>
                                </div>
                            </div>
                        </div>

                        <!-- Card: Backups -->
                        <div class="card">
                            <div class="card-header">
                                <span class="card-icon">💾</span>
                                Sistema de Backups
                            </div>
                            <div class="stat">
                                <span class="stat-label">Quantidade</span>
                                <span class="stat-value">{backup_count} arquivos</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Tamanho Total</span>
                                <span class="stat-value">{backup_size_mb} MB</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Backup 24h</span>
                                <span class="stat-value">{'✓ Ativo' if backup_24h else '✗ Inativo'}</span>
                            </div>
                            <div class="status-badge" style="margin-top: 12px;">
                                ✓ Agendador Ativo
                            </div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">
                                Daily 00:05 • Weekly Sun 02:00
                            </div>
                        </div>

                        <!-- Card: Backups Recentes -->
                        <div class="card">
                            <div class="card-header">
                                <span class="card-icon">📋</span>
                                Backups Recentes
                            </div>
                            {backup_list_html if backup_list_html else '<div style="color: #94a3b8; font-size: 13px;">Nenhum backup encontrado</div>'}
                        </div>

                        <!-- Card: Configuração -->
                        <div class="card">
                            <div class="card-header">
                                <span class="card-icon">⚙️</span>
                                Configuração
                            </div>
                            <div class="stat">
                                <span class="stat-label">Caminho BD</span>
                                <span class="stat-value" style="font-size: 12px;">{db_file_path}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Backups</span>
                                <span class="stat-value" style="font-size: 12px;">{backup_dir}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Modo</span>
                                <span class="stat-value">Production</span>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            return html
        except Exception as e:
            import traceback

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto';
                        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        color: #e2e8f0;
                        padding: 24px;
                    }}
                    .error {{
                        background: rgba(239, 68, 68, 0.1);
                        border: 1px solid #ef4444;
                        border-radius: 12px;
                        padding: 24px;
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                    h2 {{ color: #ef4444; margin-bottom: 12px; }}
                    pre {{
                        background: #1e293b;
                        padding: 12px;
                        border-radius: 6px;
                        overflow-x: auto;
                        font-size: 12px;
                        color: #94a3b8;
                    }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>❌ Erro no Diagnóstico</h2>
                    <pre>{traceback.format_exc()}</pre>
                </div>
            </body>
            </html>
            """
            return html, 500


def _perform_backup(app: Flask, retain_count: int = 20, force: bool = False, daily: bool = False) -> bool:  # noqa: C901
    """Cria um backup do banco SQLite no diretório de backups.

    - Quando daily=True, cria/atualiza o arquivo backup-24h.sqlite.
    - Caso contrário, cria arquivo com timestamp: multimax_YYYYMMDD_HHMMSS.sqlite.
    - Mantém no máximo `retain_count` backups (exceto o diário) por ordem de modificação.
    """
    try:
        with app.app_context():
            bdir = str(app.config.get("BACKUP_DIR") or "").strip()
            db_path = str(app.config.get("DB_FILE_PATH") or "").strip()

            if not bdir or not db_path:
                app.logger.warning("Configuração de BACKUP_DIR/DB_FILE_PATH inválida para backup")
                return False

            os.makedirs(bdir, exist_ok=True)

            # Somente suportado para SQLite local
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            is_sqlite = isinstance(uri, str) and uri.startswith("sqlite:")
            if not is_sqlite:
                app.logger.warning("Backup automático disponível apenas para SQLite")
                return False

            from datetime import datetime

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = os.path.join(bdir, "backup-24h.sqlite" if daily else f"multimax_{ts}.sqlite")

            try:
                import sqlite3

                # Usar VACUUM INTO para backup consistente sem travas
                conn = sqlite3.connect(db_path)
                conn.execute(f"VACUUM INTO '{target}'")
                conn.close()
            except Exception as e:
                # Fallback: cópia direta do arquivo
                app.logger.warning(f"VACUUM INTO falhou, aplicando cópia direta: {e}")
                try:
                    shutil.copy2(db_path, target)
                except Exception as e2:
                    app.logger.error(f"Falha ao copiar banco para backup: {e2}")
                    return False

            # Retenção de backups (não remove backup diário)
            try:
                items = []
                for name in os.listdir(bdir):
                    path = os.path.join(bdir, name)
                    if os.path.isfile(path) and name.endswith(".sqlite") and not name.startswith("backup-24h"):
                        try:
                            mt = os.path.getmtime(path)
                        except Exception:
                            mt = 0
                        items.append((mt, path))
                items.sort(key=lambda t: t[0], reverse=True)
                for mt, path in items[retain_count:]:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            except Exception:
                pass

            app.logger.info(f"Backup criado em: {target}")
            return True
    except Exception as e:
        try:
            app.logger.error(f"Erro ao criar backup: {e}")
        except Exception:
            pass
        return False


def _setup_maintenance_mode(app: Flask) -> None:
    """Configura middleware para modo de manutenÃ§Ã£o."""
    maintenance_mode = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

    if not maintenance_mode:
        return

    # Se modo de manutenÃ§Ã£o estÃ¡ ativo, adiciona middleware que intercepta todas as requisiÃ§Ãµes
    from flask import make_response, render_template

    @app.before_request
    def check_maintenance():
        """Intercepta todas as requisiÃ§Ãµes e retorna pÃ¡gina de manutenÃ§Ã£o."""
        response = make_response(render_template("maintenance.html"))
        response.status_code = 503
        response.headers["Retry-After"] = "3600"  # Sugere retry em 1 hora
        return response


def create_app():
    """FunÃ§Ã£o principal de criaÃ§Ã£o da aplicaÃ§Ã£o Flask."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    _load_env(os.path.join(base_dir, ".env.txt"))

    app = _create_flask_app(base_dir)

    # Verificar modo de manutenÃ§Ã£o ANTES de qualquer inicializaÃ§Ã£o
    maintenance_mode = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

    if maintenance_mode:
        # Modo de manutenÃ§Ã£o: nÃ£o inicializar banco de dados, nÃ£o registrar blueprints
        app.logger.warning("âš ï¸  MODO DE MANUTENÃ‡ÃƒO ATIVO - Sistema bloqueado")
        _setup_maintenance_mode(app)
        return app

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
