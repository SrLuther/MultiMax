import os
import sys
import threading
import time
import shutil
from flask import Flask
from typing import cast
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def _load_env(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

def _normalize_db_uri(uri: str | None) -> str | None:
    try:
        s = uri or ''
        if s and s.startswith('postgresql://'):
            s = 'postgresql+psycopg://' + s.split('://', 1)[1]
        if s and s.startswith('postgres://'):
            s = 'postgresql+psycopg://' + s.split('://', 1)[1]
        if s and ('.supabase.co' in s) and ('@' in s):
            pre, post = s.split('@', 1)
            rest = post.split('/', 1)[1] if '/' in post else ''
            hostport = 'aws-1-sa-east-1.pooler.supabase.com:5432'
            s = pre + '@' + hostport + ('/' + rest if rest else '')
        if s and s.startswith('postgresql+psycopg://'):
            if 'sslmode=' not in s:
                s = s + ('&sslmode=require' if '?' in s else '?sslmode=require')
            if 'connect_timeout=' not in s:
                s = s + ('&connect_timeout=3' if '?' in s else '?connect_timeout=3')
        return s or uri
    except Exception:
        return uri

def _extract_driver_host(uri: str) -> tuple[str | None, str | None]:
    try:
        if '://' not in uri:
            return None, None
        driver = uri.split('://', 1)[0]
        after = uri.split('://', 1)[1]
        hostpart = after.split('@', 1)[1] if '@' in after else after
        host = hostpart.split('/', 1)[0]
        return driver, host
    except Exception:
        return None, None

def create_app():
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
    _load_env(os.path.join(base_dir, '.env.txt'))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )
    # Definir caminho do banco de dados SQLite (caminho absoluto)
    # Prioridade: DB_FILE_PATH > padrão /multimax-data/estoque.db (dentro do container) ou /opt/multimax-data/estoque.db (fora do container)
    db_file_path_env = os.getenv('DB_FILE_PATH')
    if db_file_path_env:
        # Se DB_FILE_PATH foi definido, usar diretamente
        db_path = os.path.abspath(db_file_path_env).replace('\\', '/')
    else:
        # Caminho padrão absoluto
        # Dentro do Docker: /multimax-data/estoque.db (mapeado de /opt/multimax-data no host)
        # Fora do Docker: /opt/multimax-data/estoque.db
        if os.path.exists('/multimax-data'):
            # Dentro do container Docker
            db_path = '/multimax-data/estoque.db'
        else:
            # Fora do container (desenvolvimento local)
            db_path = '/opt/multimax-data/estoque.db'
    
    # Garantir que o diretório do banco existe
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    # Definir data_dir para backups e outras funcionalidades
    data_dir = (os.getenv('DATA_DIR') or os.getenv('MULTIMAX_DATA_DIR') or None)
    if not data_dir:
        # Usar o mesmo diretório do banco de dados
        data_dir = db_dir if db_dir else ('/multimax-data' if os.path.exists('/multimax-data') else '/opt/multimax-data')
    data_dir_str = cast(str, data_dir)
    os.makedirs(data_dir_str, exist_ok=True)
    
    uri_env = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    uri_env = _normalize_db_uri(uri_env)
    selected_uri = uri_env if uri_env else ('sqlite:///' + db_path)
    app.config['SQLALCHEMY_DATABASE_URI'] = selected_uri
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_secreta_muito_forte_e_aleatoria')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PER_PAGE'] = 10
    app.config['DATA_DIR'] = data_dir_str
    backup_dir = os.path.join(data_dir_str, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    app.config['BACKUP_DIR'] = backup_dir
    if isinstance(selected_uri, str) and selected_uri.startswith('sqlite:'):
        try:
            p = selected_uri.split('sqlite:///', 1)[1]
            if '?' in p:
                p = p.split('?', 1)[0]
            app.config['DB_FILE_PATH'] = p
        except Exception:
            app.config['DB_FILE_PATH'] = db_path

    db.init_app(app)
    login_manager.init_app(app)
    setattr(login_manager, 'login_view', 'auth.login')
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    from .models import User, Produto, CleaningTask, NotificationRead, AppSetting

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

    from .routes.auth import bp as auth_bp
    from .routes.home import bp as home_bp
    from .routes.estoque import bp as estoque_bp
    from .routes.cronograma import bp as cronograma_bp, setup_cleaning_tasks
    from .routes.exportacao import bp as exportacao_bp
    from .routes.usuarios import bp as usuarios_bp
    from .routes.carnes import bp as carnes_bp
    from .routes.colaboradores import bp as colaboradores_bp
    from .routes.receitas import bp as receitas_bp
    from .routes.relatorios import bp as relatorios_bp
    from .routes.api import bp as api_bp
    from .routes.jornada import bp as jornada_bp
    try:
        from .routes.temporarios import bp as temporarios_bp
    except Exception:
        temporarios_bp = None
    notif_enabled = (os.getenv('NOTIFICACOES_ENABLED', 'false') or 'false').lower() == 'true'
    notificacoes_bp = None
    if notif_enabled:
        try:
            from .routes.notificacoes import bp as _notifs
            notificacoes_bp = _notifs
        except Exception:
            notificacoes_bp = None
    try:
        from .routes.dbadmin import bp as dbadmin_bp
        app.logger.info(f'Blueprint dbadmin importado com sucesso. URL prefix: {dbadmin_bp.url_prefix}')
    except Exception as e:
        app.logger.error(f'Erro ao importar blueprint dbadmin: {e}', exc_info=True)
        dbadmin_bp = None

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(cronograma_bp)
    app.register_blueprint(exportacao_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carnes_bp)
    app.register_blueprint(colaboradores_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(jornada_bp)
    if temporarios_bp:
        app.register_blueprint(temporarios_bp)
    if notificacoes_bp:
        app.register_blueprint(notificacoes_bp)
    if dbadmin_bp:
        app.register_blueprint(dbadmin_bp)
        app.logger.info(f'Blueprint dbadmin registrado com sucesso. Rotas disponíveis: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("dbadmin.")]}')
    else:
        app.logger.warning('Blueprint dbadmin não foi registrado (dbadmin_bp é None)')

    @app.context_processor
    def _inject_version():
        ver = (os.getenv('APP_VERSION') or '').strip()
        if not ver:
            try:
                import subprocess
                base_dir = os.path.dirname(os.path.dirname(__file__))
                r = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                                 cwd=base_dir, capture_output=True, text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    ver = r.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                pass
            except Exception as e:
                app.logger.warning(f"Erro ao obter versão do git: {e}")
            if not ver:
                try:
                    s = AppSetting.query.filter_by(key='app_version').first()
                    ver = (s.value or '').strip() if s else ''
                except Exception as e:
                    app.logger.warning(f"Erro ao obter versão do banco: {e}")
                    ver = ''
        return {'git_version': ver or 'dev'}

    @app.route('/', strict_slashes=False)
    def _root_redirect():
        from flask_login import current_user
        from flask import redirect, url_for
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return redirect(url_for('home.index'))

    @app.route('/health', strict_slashes=False)
    def _health():
        return 'ok', 200

    @app.route('/dbstatus', strict_slashes=False)
    def _dbstatus():
        try:
            from sqlalchemy import text
            from flask import url_for
            from datetime import datetime
            uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            ok = False
            err = ''
            db_version = '-'
            db_size = '-'
            tables_count = 0
            uptime = '-'
            try:
                db.session.execute(text('select 1'))
                ok = True
                if 'postgresql' in uri.lower():
                    try:
                        result = db.session.execute(text("SELECT version()")).fetchone()
                        if result:
                            ver = str(result[0])
                            db_version = ver.split(',')[0] if ',' in ver else ver[:50]
                    except Exception:
                        pass
                    try:
                        result = db.session.execute(text("SELECT pg_database_size(current_database())")).fetchone()
                        if result:
                            size_bytes = result[0]
                            if size_bytes > 1024*1024*1024:
                                db_size = f"{size_bytes/1024/1024/1024:.2f} GB"
                            elif size_bytes > 1024*1024:
                                db_size = f"{size_bytes/1024/1024:.2f} MB"
                            else:
                                db_size = f"{size_bytes/1024:.2f} KB"
                    except Exception:
                        pass
                    try:
                        result = db.session.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")).fetchone()
                        if result:
                            tables_count = result[0]
                    except Exception:
                        pass
                elif 'sqlite' in uri.lower():
                    db_version = 'SQLite 3'
                    try:
                        import os
                        db_path = uri.replace('sqlite:///', '')
                        if os.path.exists(db_path):
                            size_bytes = os.path.getsize(db_path)
                            if size_bytes > 1024*1024:
                                db_size = f"{size_bytes/1024/1024:.2f} MB"
                            else:
                                db_size = f"{size_bytes/1024:.2f} KB"
                    except Exception:
                        pass
                    try:
                        result = db.session.execute(text("SELECT count(*) FROM sqlite_master WHERE type='table'")).fetchone()
                        if result:
                            tables_count = result[0]
                    except Exception:
                        pass
            except Exception as e:
                err = str(e)
                try:
                    db.session.rollback()
                except Exception:
                    pass
            driver, host = _extract_driver_host(uri)
            status_code = 200 if ok else 503
            pulse_animation = '@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }' if ok else ''
            html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Status do Banco de Dados</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --mm-bg: #0a0a0a;
      --mm-surface: #111111;
      --mm-surface-2: #1a1a1a;
      --mm-surface-3: #222222;
      --mm-border: rgba(255, 255, 255, 0.06);
      --mm-border-glow: rgba(16, 185, 129, 0.3);
      --mm-text: #f5f5f5;
      --mm-text-muted: #888888;
      --mm-primary: #3b82f6;
      --mm-success: #10b981;
      --mm-danger: #ef4444;
      --mm-warning: #f59e0b;
      --mm-cyan: #06b6d4;
      --mm-purple: #8b5cf6;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--mm-bg);
      color: var(--mm-text);
      padding: 20px;
      min-height: 100vh;
    }}
    {pulse_animation}
    .db-container {{
      max-width: 100%;
    }}
    .db-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--mm-border);
    }}
    .db-title {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .db-title-icon {{
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: {'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1))' if ok else 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.1))'};
      border: 1px solid {'rgba(16, 185, 129, 0.3)' if ok else 'rgba(239, 68, 68, 0.3)'};
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      color: {'var(--mm-success)' if ok else 'var(--mm-danger)'};
    }}
    .db-title h1 {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 2px;
    }}
    .db-title p {{
      font-size: 12px;
      color: var(--mm-text-muted);
    }}
    .db-status-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 50px;
      font-size: 13px;
      font-weight: 600;
      background: {'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))' if ok else 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(185, 28, 28, 0.08))'};
      border: 1px solid {'rgba(16, 185, 129, 0.3)' if ok else 'rgba(239, 68, 68, 0.3)'};
      color: {'var(--mm-success)' if ok else 'var(--mm-danger)'};
    }}
    .db-status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: {'var(--mm-success)' if ok else 'var(--mm-danger)'};
      {'animation: pulse 2s infinite;' if ok else ''}
    }}
    .db-kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }}
    .db-kpi-card {{
      background: var(--mm-surface);
      border: 1px solid var(--mm-border);
      border-radius: 12px;
      padding: 16px;
      position: relative;
      overflow: hidden;
    }}
    .db-kpi-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
    }}
    .db-kpi-card.kpi-status::before {{ background: {'var(--mm-success)' if ok else 'var(--mm-danger)'}; }}
    .db-kpi-card.kpi-version::before {{ background: var(--mm-primary); }}
    .db-kpi-card.kpi-size::before {{ background: var(--mm-cyan); }}
    .db-kpi-card.kpi-tables::before {{ background: var(--mm-purple); }}
    .db-kpi-icon {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      margin-bottom: 12px;
    }}
    .kpi-status .db-kpi-icon {{ background: {'rgba(16, 185, 129, 0.15)' if ok else 'rgba(239, 68, 68, 0.15)'}; color: {'var(--mm-success)' if ok else 'var(--mm-danger)'}; }}
    .kpi-version .db-kpi-icon {{ background: rgba(59, 130, 246, 0.15); color: var(--mm-primary); }}
    .kpi-size .db-kpi-icon {{ background: rgba(6, 182, 212, 0.15); color: var(--mm-cyan); }}
    .kpi-tables .db-kpi-icon {{ background: rgba(139, 92, 246, 0.15); color: var(--mm-purple); }}
    .db-kpi-label {{
      font-size: 11px;
      color: var(--mm-text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }}
    .db-kpi-value {{
      font-size: 18px;
      font-weight: 700;
      color: var(--mm-text);
    }}
    .db-info-section {{
      background: var(--mm-surface);
      border: 1px solid var(--mm-border);
      border-radius: 12px;
      overflow: hidden;
    }}
    .db-info-header {{
      padding: 14px 16px;
      background: var(--mm-surface-2);
      border-bottom: 1px solid var(--mm-border);
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .db-info-header i {{ color: var(--mm-primary); }}
    .db-info-row {{
      display: flex;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--mm-border);
    }}
    .db-info-row:last-child {{ border-bottom: none; }}
    .db-info-label {{
      min-width: 100px;
      font-size: 12px;
      color: var(--mm-text-muted);
      font-weight: 500;
    }}
    .db-info-value {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--mm-text);
      word-break: break-all;
    }}
    .db-info-value.success {{ color: var(--mm-success); }}
    .db-info-value.error {{ color: var(--mm-danger); }}
    @media (max-width: 600px) {{
      .db-kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .db-header {{ flex-direction: column; gap: 12px; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="db-container">
    <div class="db-header">
      <div class="db-title">
        <div class="db-title-icon">
          <i class="bi bi-database{'-fill' if ok else '-x'}"></i>
        </div>
        <div>
          <h1>Conexao ao Banco de Dados</h1>
          <p>Diagnostico em tempo real</p>
        </div>
      </div>
      <div class="db-status-badge">
        <span class="db-status-dot"></span>
        {'Conectado' if ok else 'Desconectado'}
      </div>
    </div>
    
    <div class="db-kpi-grid">
      <div class="db-kpi-card kpi-status">
        <div class="db-kpi-icon"><i class="bi bi-{'check-circle' if ok else 'x-circle'}"></i></div>
        <div class="db-kpi-label">Status</div>
        <div class="db-kpi-value">{'Online' if ok else 'Offline'}</div>
      </div>
      <div class="db-kpi-card kpi-version">
        <div class="db-kpi-icon"><i class="bi bi-tag"></i></div>
        <div class="db-kpi-label">Versao</div>
        <div class="db-kpi-value">{db_version[:20] if len(db_version) > 20 else db_version}</div>
      </div>
      <div class="db-kpi-card kpi-size">
        <div class="db-kpi-icon"><i class="bi bi-hdd"></i></div>
        <div class="db-kpi-label">Tamanho</div>
        <div class="db-kpi-value">{db_size}</div>
      </div>
      <div class="db-kpi-card kpi-tables">
        <div class="db-kpi-icon"><i class="bi bi-table"></i></div>
        <div class="db-kpi-label">Tabelas</div>
        <div class="db-kpi-value">{tables_count}</div>
      </div>
    </div>
    
    <div class="db-info-section">
      <div class="db-info-header">
        <i class="bi bi-gear"></i>
        Detalhes da Conexao
      </div>
      <div class="db-info-row">
        <span class="db-info-label">Servidor</span>
        <span class="db-info-value">{host or 'localhost'}</span>
      </div>
      <div class="db-info-row">
        <span class="db-info-label">Driver</span>
        <span class="db-info-value">{driver or 'SQLite'}</span>
      </div>
      <div class="db-info-row">
        <span class="db-info-label">Status</span>
        <span class="db-info-value {'success' if ok else 'error'}">{err if err else ('Conexao funcionando normalmente' if ok else 'Falha na conexao')}</span>
      </div>
    </div>
  </div>
</body>
</html>"""
            return html, status_code
        except Exception as e:
            return f"erro={e}", 500

    

    @app.context_processor
    def inject_notifications():
        try:
            from datetime import date
            from flask import url_for, request, current_app
            from flask_login import current_user
            if not current_app.config.get('DB_OK', True):
                return {'notif_items': [], 'notif_count': 0}
            if not current_user.is_authenticated:
                return {'notif_items': [], 'notif_count': 0}
            nf = request.args.get('nf', '').strip()
            cat = request.args.get('cat', '').strip().upper()  # categoria estoque: CX/PC/VA/AV
            today = date.today()
            low_stock = []
            overdue = []
            if nf != 'limpeza':
                low_stock = (
                    Produto.query.with_entities(Produto.id, Produto.nome, Produto.quantidade, Produto.estoque_minimo, Produto.codigo)
                    .filter(Produto.quantidade <= Produto.estoque_minimo)
                    .order_by(Produto.quantidade.asc(), Produto.nome.asc())
                    .limit(10)
                    .all()
                )
            if nf != 'estoque':
                overdue = (
                    CleaningTask.query.with_entities(CleaningTask.id, CleaningTask.nome_limpeza, CleaningTask.proxima_data)
                    .filter(CleaningTask.proxima_data < today)
                    .order_by(CleaningTask.proxima_data.asc())
                    .limit(10)
                    .all()
                )
            reads = NotificationRead.query.with_entities(NotificationRead.tipo, NotificationRead.ref_id).filter_by(user_id=current_user.id).all()
            read_set = {(r[0], r[1]) for r in reads}
            items = []
            for p in low_stock:
                categoria = (p.codigo or '').split('-', 1)[0]
                if nf == 'limpeza':
                    pass
                else:
                    if cat and categoria != cat:
                        pass
                    else:
                        sev = 2 if (p.quantidade or 0) == 0 else 1
                        if ('estoque', p.id) not in read_set:
                            items.append({
                                'tipo': 'estoque',
                                'id': p.id,
                                'categoria': categoria,
                                'titulo': p.nome,
                                'descricao': f"Estoque baixo: {p.quantidade}/{p.estoque_minimo}",
                                'url': url_for('estoque.editar', id=p.id),
                                'sev': sev,
                            })
            for t in overdue:
                if nf == 'estoque':
                    pass
                else:
                    days = (today - t.proxima_data).days
                    sev = 2 if days >= 7 else 1
                    if ('limpeza', t.id) not in read_set:
                        items.append({
                            'tipo': 'limpeza',
                            'id': t.id,
                            'titulo': t.nome_limpeza,
                            'descricao': f"Atrasada desde {t.proxima_data.strftime('%d/%m/%Y')}",
                            'url': url_for('cronograma.cronograma'),
                            'sev': sev,
                        })
            items.sort(key=lambda x: (x['sev'], x['tipo']), reverse=True)
            return {'notif_items': items, 'notif_count': len(items)}
        except Exception:
            return {'notif_items': [], 'notif_count': 0}

    def _get_version():
        v = os.getenv('APP_VERSION')
        if v:
            return v
        try:
            import subprocess
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
            r = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                             cwd=base_dir, capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
            r2 = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              cwd=base_dir, capture_output=True, text=True, timeout=2)
            if r2.returncode == 0 and r2.stdout.strip():
                return r2.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        except Exception as e:
            # Log apenas se não for erro esperado (git não disponível)
            if 'git' not in str(e).lower():
                app.logger.debug(f"Erro ao obter versão: {e}")
            return '2.3.27'

    resolved_version = _get_version()
    app.config['APP_VERSION_RESOLVED'] = resolved_version.lstrip('vV') if isinstance(resolved_version, str) else resolved_version

    @app.context_processor
    def inject_version():
        return {'git_version': app.config.get('APP_VERSION_RESOLVED', 'dev')}

    with app.app_context():
        try:
            from .models import AppSetting
            import subprocess
            import json
            from urllib import request as urllib_request
            from urllib import error as urllib_error
            ver = app.config.get('APP_VERSION_RESOLVED', 'dev')
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
            commits = []
            last_tag = None
            try:
                r = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], cwd=base_dir, capture_output=True, text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    last_tag = r.stdout.strip()
                if last_tag:
                    rlog = subprocess.run(['git', 'log', '--pretty=%h %s', f'{last_tag}..HEAD'], cwd=base_dir, capture_output=True, text=True, timeout=3)
                    if rlog.returncode == 0:
                        commits = [line.strip() for line in rlog.stdout.splitlines() if line.strip()]
                else:
                    rlog2 = subprocess.run(['git', 'log', '-n', '20', '--pretty=%h %s'], cwd=base_dir, capture_output=True, text=True, timeout=3)
                    if rlog2.returncode == 0:
                        commits = [line.strip() for line in rlog2.stdout.splitlines() if line.strip()]
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                try:
                    req = urllib_request.Request('https://api.github.com/repos/SrLuther/MultiMax/commits?sha=main')
                    req.add_header('User-Agent', 'MultiMax-App')
                    with urllib_request.urlopen(req, timeout=5) as resp:
                        raw = resp.read().decode('utf-8')
                        arr = json.loads(raw)
                        for it in arr[:20]:
                            h = (it.get('sha') or '')[:7]
                            msg = ((it.get('commit') or {}).get('message') or '').split('\n',1)[0]
                            if msg:
                                commits.append(f'{h} {msg}')
                except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError):
                    commits = []
                except Exception as e:
                    app.logger.warning(f"Erro ao buscar commits do GitHub: {e}")
                    commits = []
            curated = [
                'Segurança: ajuste de permissões para Visualizador',
                'Escala: Domingos/Feriados restritos a Administrador',
                'Colaboradores: criação automática da coluna name (DB fix)',
                'Correção: acesso seguro ao nome do colaborador',
                'Relatórios de carnes: tabelas mais densas e legíveis',
                'Dependências: atualizações e imports corrigidos',
                'Versão de segurança publicada'
            ]
            commits = curated
            head = f'v{ver}' if isinstance(ver, str) else str(ver)
            lines = [f'{head}'] + [f'- {c}' for c in commits]
            txt = '\n'.join(lines)
            try:
                s = AppSetting.query.filter_by(key='changelog_text').first()
                if not s:
                    s = AppSetting(); s.key = 'changelog_text'; db.session.add(s)
                    s.value = txt
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        except Exception:
            pass
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
        if is_sqlite:
            db.create_all()
            try:
                from sqlalchemy import text
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_produto_nome ON produto (nome)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_produto_codigo ON produto (codigo)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_produto_quantidade ON produto (quantidade)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_produto_minimo ON produto (estoque_minimo)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_historico_product ON historico (product_id)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_historico_data ON historico (data)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_historico_action ON historico (action)'))
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        db_ok = True
        if not is_sqlite:
            try:
                from sqlalchemy import text
                db.session.execute(text('select 1'))
            except Exception:
                db_ok = False
        app.config['DB_OK'] = db_ok
        app.config['DB_IS_SQLITE'] = is_sqlite
        try:
            from sqlalchemy import inspect
            # Importar TODOS os modelos para garantir que estejam no metadata
            # Isso é crítico para que db.create_all() crie todas as tabelas automaticamente
            # Importação explícita garante que SQLAlchemy registre todas as tabelas
            try:
                from .models import (
                    User, Collaborator, Produto, Historico, CleaningTask, CleaningHistory,
                    CleaningChecklistTemplate, CleaningChecklistItem, CleaningHistoryPhoto,
                    NotificationRead, AppSetting, TimeOffRecord, Holiday, SystemLog, 
                    Vacation, MedicalCertificate, JornadaArchive, MonthStatus, Shift, 
                    TemporaryEntry, JobRole, MeatReception, MeatCarrier, MeatPart,
                    NotificacaoDiaria, NotificacaoPersonalizada, EventoDoDia,
                    Recipe, RecipeIngredient, UserLogin, Incident, MetricHistory,
                    Alert, MaintenanceLog, QueryLog, BackupVerification,
                    IngredientCatalog, CustomSchedule, HelpArticle,
                    RegistroJornada, RegistroJornadaChange, ArticleVote,
                    Suggestion, SuggestionVote
                )
            except ImportError as import_err:
                app.logger.warning(f'Erro ao importar alguns modelos: {import_err}. Continuando...')
                # Tentar importação alternativa - importar tudo de uma vez
                try:
                    from . import models
                    app.logger.info('Modelos importados via importação de módulo completo')
                except Exception as alt_err:
                    app.logger.error(f'Erro na importação alternativa de modelos: {alt_err}', exc_info=True)
            
            # Verificar quais tabelas existem e quais devem existir
            try:
                insp = inspect(db.engine)
                existing_tables = set(insp.get_table_names())
                declared_tables = set(db.metadata.tables.keys())
                
                # Se houver tabelas declaradas que não existem, criar todas automaticamente
                missing_tables = declared_tables - existing_tables
                if missing_tables:
                    app.logger.info(f'Criando automaticamente {len(missing_tables)} tabela(s) ausente(s): {missing_tables}')
                    db.create_all()
                    db.session.commit()
                    app.logger.info('Tabelas criadas automaticamente com sucesso')
                else:
                    app.logger.debug('Todas as tabelas necessárias já existem no banco de dados')
            except Exception as inspect_err:
                app.logger.warning(f'Erro ao verificar tabelas: {inspect_err}. Tentando criar todas...')
                try:
                    db.create_all()
                    db.session.commit()
                    app.logger.info('Tabelas criadas com sucesso (modo fallback)')
                except Exception as create_err:
                    app.logger.error(f'Erro ao criar tabelas: {create_err}', exc_info=True)
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
        except Exception as e:
            app.logger.error(f'Erro geral ao verificar/criar tabelas: {e}', exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass
            # Tentar criar todas as tabelas mesmo em caso de erro (fallback final)
            try:
                app.logger.warning('Tentando criar todas as tabelas como fallback final...')
                db.create_all()
                db.session.commit()
                app.logger.info('Tabelas criadas com sucesso (fallback final)')
            except Exception as create_error:
                app.logger.error(f'Erro ao criar tabelas (fallback final): {create_error}', exc_info=True)
                try:
                    db.session.rollback()
                except Exception:
                    pass
        if not is_sqlite and db_ok:
            try:
                from sqlalchemy import text
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE TEXT'))
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        if not is_sqlite and db_ok:
            try:
                from sqlalchemy import text
                db.session.execute(text('alter table public."meat_reception" add column if not exists reference_code text'))
                role = None
                try:
                    uri_s = str(uri)
                    if '://' in uri_s:
                        creds = uri_s.split('://', 1)[1].split('@', 1)[0]
                        role = creds.split(':', 1)[0]
                        if role.startswith('postgres.'):
                            role = 'postgres'
                except Exception:
                    pass
                tables = [
                    'cleaning_task','cleaning_history','system_log','notification_read','app_setting',
                    'produto','historico','meat_reception','meat_carrier','meat_part','collaborator',
                    'shift','leave_credit','hour_bank_entry','leave_assignment','leave_conversion','user','holiday'
                ]
                for t in tables:
                    try:
                        db.session.execute(text(f'alter table public."{t}" enable row level security'))
                    except Exception:
                        pass
                    if role:
                        try:
                            db.session.execute(text(f'drop policy if exists allow_server_all on public."{t}"'))
                        except Exception:
                            pass
                        try:
                            db.session.execute(text(f'create policy allow_server_all on public."{t}" for all to "{role}" using (true) with check (true)'))
                        except Exception:
                            pass
                db.session.commit()
                try:
                    from sqlalchemy import text
                    db.session.execute(text('create index if not exists idx_produto_nome on produto (nome)'))
                    db.session.execute(text('create index if not exists idx_hist_product_date on historico (product_id, data)'))
                    db.session.execute(text('create index if not exists idx_notif_user_ref on notification_read (user_id, ref_id)'))
                    db.session.execute(text('create index if not exists idx_cleaningtask_proxima on cleaning_task (proxima_data)'))
                    db.session.execute(text('create index if not exists idx_shift_collab_date on shift (collaborator_id, date)'))
                    db.session.execute(text('create index if not exists idx_produto_codigo on produto (codigo)'))
                    db.session.execute(text('create index if not exists idx_produto_quantidade on produto (quantidade)'))
                    db.session.execute(text('create index if not exists idx_produto_minimo on produto (estoque_minimo)'))
                    db.session.execute(text('create index if not exists idx_historico_action on historico (action)'))
                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        if db_ok:
            try:
                from .models import Produto
                rows = Produto.query.filter(Produto.nome == 'ciano').all()
                for r in rows:
                    db.session.delete(r)
                if rows:
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
            try:
                s_ver = AppSetting.query.filter_by(key='app_version').first()
                if not s_ver:
                    s_ver = AppSetting(); s_ver.key = 'app_version'; db.session.add(s_ver)
                cur_ver = (os.getenv('APP_VERSION') or '').strip()
                if not cur_ver:
                    try:
                        import subprocess
                        base_dir = os.path.dirname(os.path.dirname(__file__))
                        r = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                                         cwd=base_dir, capture_output=True, text=True, timeout=2)
                        if r.returncode == 0 and r.stdout.strip():
                            cur_ver = r.stdout.strip()
                        else:
                            cur_ver = (s_ver.value or '').strip()
                    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                        cur_ver = (s_ver.value or '').strip()
                    except Exception as e:
                        app.logger.warning(f"Erro ao obter versão: {e}")
                        cur_ver = (s_ver.value or '').strip()
                s_ver.value = cur_ver
                s_ch = AppSetting.query.filter_by(key='changelog_text').first()
                if not s_ch:
                    s_ch = AppSetting(); s_ch.key = 'changelog_text'; db.session.add(s_ch)
                from datetime import date as _date
                s_ch.value = (
                    f"Release 1.3.3.1 — {_date.today().strftime('%Y-%m-%d')}\n"
                    "- Banco de Dados: painel com backups e diagnóstico embutido\n"
                    "- Backup automático por hora com retenção dos 10 mais recentes\n"
                    "- Carnes: Frango com múltiplos pesos antes de salvar\n"
                    "- Carnes: Suína com 'Pesos' e tara por item\n"
                    "- PDF de Carnes: seção de cálculos mostra o tipo (Bovina/Suína/Frango)\n"
                    "- Menu: link Banco de Dados visível apenas para gerente\n"
                )
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
            # Usuário Desenvolvedor (DEV) - única senha padrão no sistema
            if User.query.filter_by(username='dev').first() is None:
                try:
                    dev = User()
                    dev.name = 'Desenvolvedor'
                    dev.username = 'dev'
                    dev.nivel = 'DEV'
                    from multimax.password_hash import generate_password_hash
                    dev.password_hash = generate_password_hash(os.getenv('SENHA_DEV', 'maxpowerdev963'))
                    db.session.add(dev)
                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            else:
                try:
                    from multimax.password_hash import generate_password_hash
                    env_pwd = os.getenv('SENHA_DEV')
                    if env_pwd:
                        dev = User.query.filter_by(username='dev').first()
                        if dev:
                            dev.password_hash = generate_password_hash(env_pwd)
                            db.session.commit()
                    else:
                        # Atualizar senha padrão se não houver variável de ambiente
                        dev = User.query.filter_by(username='dev').first()
                        if dev:
                            dev.password_hash = generate_password_hash('maxpowerdev963')
                            db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            setup_cleaning_tasks()
        if is_sqlite:
            try:
                from sqlalchemy import text
                res = db.session.execute(text('PRAGMA table_info(meat_part)'))
                cols = []
                for row in res:
                    cols.append(row[1])
                if 'tara' not in cols:
                    db.session.execute(text('ALTER TABLE meat_part ADD COLUMN tara REAL DEFAULT 0'))
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

        if is_sqlite:
            try:
                from sqlalchemy import text
                res = db.session.execute(text('PRAGMA table_info(meat_reception)'))
                cols = [row[1] for row in res]
                if 'reference_code' not in cols:
                    db.session.execute(text('ALTER TABLE meat_reception ADD COLUMN reference_code TEXT'))
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

        if is_sqlite:
            try:
                from sqlalchemy import text
                res = db.session.execute(text('PRAGMA table_info(collaborator)'))
                cols = [row[1] for row in res]
                if 'regular_team' not in cols:
                    db.session.execute(text('ALTER TABLE collaborator ADD COLUMN regular_team TEXT'))
                    db.session.commit()
                if 'sunday_team' not in cols:
                    db.session.execute(text('ALTER TABLE collaborator ADD COLUMN sunday_team TEXT'))
                    db.session.commit()
                if 'special_team' not in cols:
                    db.session.execute(text('ALTER TABLE collaborator ADD COLUMN special_team TEXT'))
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

        if is_sqlite:
            try:
                from sqlalchemy import text
                res = db.session.execute(text('PRAGMA table_info(shift)'))
                cols = [row[1] for row in res]
                if 'start_dt' not in cols:
                    db.session.execute(text('ALTER TABLE shift ADD COLUMN start_dt TEXT'))
                    db.session.commit()
                if 'end_dt' not in cols:
                    db.session.execute(text('ALTER TABLE shift ADD COLUMN end_dt TEXT'))
                    db.session.commit()
                if 'shift_type' not in cols:
                    db.session.execute(text('ALTER TABLE shift ADD COLUMN shift_type TEXT'))
                    db.session.commit()
                if 'auto_generated' not in cols:
                    db.session.execute(text('ALTER TABLE shift ADD COLUMN auto_generated INTEGER'))
                    db.session.commit()
                if 'is_sunday_holiday' not in cols:
                    db.session.execute(text('ALTER TABLE shift ADD COLUMN is_sunday_holiday INTEGER'))
                    db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('collaborator')]
            changed = False
            if 'name' not in cols:
                db.session.execute(text('ALTER TABLE collaborator ADD COLUMN name TEXT'))
                changed = True
                if 'nome' in cols:
                    try:
                        db.session.execute(text('UPDATE collaborator SET name = nome WHERE name IS NULL'))
                    except Exception:
                        pass
                else:
                    try:
                        db.session.execute(text("UPDATE collaborator SET name = '' WHERE name IS NULL"))
                    except Exception:
                        pass
            if 'matricula' not in cols:
                db.session.execute(text('ALTER TABLE collaborator ADD COLUMN matricula TEXT'))
                changed = True
            if 'departamento' not in cols:
                db.session.execute(text('ALTER TABLE collaborator ADD COLUMN departamento TEXT'))
                changed = True
            if changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            s_cols = [c['name'] for c in insp.get_columns('shift')]
            s_changed = False
            if 'start_dt' not in s_cols and not is_sqlite:
                db.session.execute(text('ALTER TABLE shift ADD COLUMN start_dt TIMESTAMPTZ'))
                s_changed = True
            if 'end_dt' not in s_cols and not is_sqlite:
                db.session.execute(text('ALTER TABLE shift ADD COLUMN end_dt TIMESTAMPTZ'))
                s_changed = True
            if 'shift_type' not in s_cols:
                db.session.execute(text('ALTER TABLE shift ADD COLUMN shift_type TEXT'))
                s_changed = True
            if 'auto_generated' not in s_cols:
                db.session.execute(text('ALTER TABLE shift ADD COLUMN auto_generated BOOLEAN'))
                s_changed = True
            if 'is_sunday_holiday' not in s_cols:
                db.session.execute(text('ALTER TABLE shift ADD COLUMN is_sunday_holiday BOOLEAN'))
                s_changed = True
            if s_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            la_cols = [c['name'] for c in insp.get_columns('leave_assignment')]
            if 'notes' not in la_cols:
                db.session.execute(text('ALTER TABLE leave_assignment ADD COLUMN notes TEXT'))
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            lc_cols = [c['name'] for c in insp.get_columns('leave_credit')]
            lc_changed = False
            if 'origin' not in lc_cols:
                db.session.execute(text('ALTER TABLE leave_credit ADD COLUMN origin TEXT'))
                lc_changed = True
            if 'notes' not in lc_cols:
                db.session.execute(text('ALTER TABLE leave_credit ADD COLUMN notes TEXT'))
                lc_changed = True
            if lc_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            hb_cols = [c['name'] for c in insp.get_columns('hour_bank_entry')]
            if 'reason' not in hb_cols:
                db.session.execute(text('ALTER TABLE hour_bank_entry ADD COLUMN reason TEXT'))
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            vac_cols = [c['name'] for c in insp.get_columns('vacation')]
            if 'observacao' not in vac_cols:
                db.session.execute(text('ALTER TABLE vacation ADD COLUMN observacao TEXT'))
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            mc_cols = [c['name'] for c in insp.get_columns('medical_certificate')]
            mc_changed = False
            if 'motivo' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN motivo TEXT'))
                mc_changed = True
            if 'cid' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN cid TEXT'))
                mc_changed = True
            if 'medico' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN medico TEXT'))
                mc_changed = True
            if 'foto_atestado' not in mc_cols:
                db.session.execute(text('ALTER TABLE medical_certificate ADD COLUMN foto_atestado TEXT'))
                mc_changed = True
            if mc_changed:
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            rj_cols = [c['name'] for c in insp.get_columns('registro_jornada')]
            if 'observacao' not in rj_cols:
                db.session.execute(text('ALTER TABLE registro_jornada ADD COLUMN observacao TEXT'))
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        # Criar tabela unificada TimeOffRecord se não existir
        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            tables = set(insp.get_table_names())
            if 'time_off_record' not in tables:
                if is_sqlite:
                    db.session.execute(text('''
                        CREATE TABLE IF NOT EXISTS time_off_record (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            collaborator_id INTEGER NOT NULL,
                            date DATE NOT NULL,
                            record_type TEXT NOT NULL,
                            hours REAL,
                            days INTEGER,
                            amount_paid REAL,
                            rate_per_day REAL,
                            origin TEXT,
                            notes TEXT,
                            created_at TIMESTAMP,
                            created_by TEXT,
                            FOREIGN KEY (collaborator_id) REFERENCES collaborator(id)
                        )
                    '''))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_collab ON time_off_record (collaborator_id)'))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_date ON time_off_record (date)'))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_type ON time_off_record (record_type)'))
                else:
                    db.session.execute(text('''
                        CREATE TABLE IF NOT EXISTS time_off_record (
                            id SERIAL PRIMARY KEY,
                            collaborator_id INTEGER NOT NULL,
                            date DATE NOT NULL,
                            record_type VARCHAR(20) NOT NULL,
                            hours REAL,
                            days INTEGER,
                            amount_paid REAL,
                            rate_per_day REAL,
                            origin VARCHAR(50),
                            notes VARCHAR(500),
                            created_at TIMESTAMPTZ,
                            created_by VARCHAR(100),
                            FOREIGN KEY (collaborator_id) REFERENCES collaborator(id)
                        )
                    '''))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_collab ON time_off_record (collaborator_id)'))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_date ON time_off_record (date)'))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_timeoff_type ON time_off_record (record_type)'))
                db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        
        # Migrar dados das tabelas antigas para TimeOffRecord (apenas uma vez)
        try:
            from sqlalchemy import inspect, text
            from datetime import datetime as _dt
            insp = inspect(db.engine)
            tables = set(insp.get_table_names())
            
            # Verificar se já foi migrado (verificando se há dados em time_off_record mas ainda há dados nas antigas)
            if 'time_off_record' in tables and ('hour_bank_entry' in tables or 'leave_credit' in tables or 'leave_assignment' in tables or 'leave_conversion' in tables):
                # Verificar se já migrou
                count_unified = db.session.execute(text('SELECT COUNT(*) FROM time_off_record')).scalar() or 0
                count_old = 0
                if 'hour_bank_entry' in tables:
                    count_old += db.session.execute(text('SELECT COUNT(*) FROM hour_bank_entry')).scalar() or 0
                if 'leave_credit' in tables:
                    count_old += db.session.execute(text('SELECT COUNT(*) FROM leave_credit')).scalar() or 0
                if 'leave_assignment' in tables:
                    count_old += db.session.execute(text('SELECT COUNT(*) FROM leave_assignment')).scalar() or 0
                if 'leave_conversion' in tables:
                    count_old += db.session.execute(text('SELECT COUNT(*) FROM leave_conversion')).scalar() or 0
                
                # Se há dados antigos mas não há na unificada, fazer migração
                if count_old > 0 and count_unified == 0:
                    now_func = "datetime('now')" if is_sqlite else "NOW()"
                    
                    # Migrar HourBankEntry
                    if 'hour_bank_entry' in tables:
                        db.session.execute(text(f'''
                            INSERT INTO time_off_record (collaborator_id, date, record_type, hours, notes, origin, created_at, created_by)
                            SELECT collaborator_id, date, 'horas', hours, COALESCE(reason, 'Horas extras'), 'migrado', {now_func}, 'sistema'
                            FROM hour_bank_entry
                            WHERE NOT EXISTS (
                                SELECT 1 FROM time_off_record tor 
                                WHERE tor.collaborator_id = hour_bank_entry.collaborator_id 
                                AND tor.date = hour_bank_entry.date 
                                AND tor.record_type = 'horas'
                                AND tor.hours = hour_bank_entry.hours
                            )
                        '''))
                    
                    # Migrar LeaveCredit
                    if 'leave_credit' in tables:
                        db.session.execute(text(f'''
                            INSERT INTO time_off_record (collaborator_id, date, record_type, days, notes, origin, created_at, created_by)
                            SELECT collaborator_id, date, 'folga_adicional', COALESCE(amount_days, 1), COALESCE(notes, 'Folga adicional'), COALESCE(origin, 'migrado'), {now_func}, 'sistema'
                            FROM leave_credit
                            WHERE NOT EXISTS (
                                SELECT 1 FROM time_off_record tor 
                                WHERE tor.collaborator_id = leave_credit.collaborator_id 
                                AND tor.date = leave_credit.date 
                                AND tor.record_type = 'folga_adicional'
                                AND tor.days = COALESCE(leave_credit.amount_days, 1)
                            )
                        '''))
                    
                    # Migrar LeaveAssignment
                    if 'leave_assignment' in tables:
                        db.session.execute(text(f'''
                            INSERT INTO time_off_record (collaborator_id, date, record_type, days, notes, origin, created_at, created_by)
                            SELECT collaborator_id, date, 'folga_usada', COALESCE(days_used, 1), COALESCE(notes, 'Folga usada'), 'migrado', {now_func}, 'sistema'
                            FROM leave_assignment
                            WHERE NOT EXISTS (
                                SELECT 1 FROM time_off_record tor 
                                WHERE tor.collaborator_id = leave_assignment.collaborator_id 
                                AND tor.date = leave_assignment.date 
                                AND tor.record_type = 'folga_usada'
                                AND tor.days = COALESCE(leave_assignment.days_used, 1)
                            )
                        '''))
                    
                    # Migrar LeaveConversion
                    if 'leave_conversion' in tables:
                        db.session.execute(text(f'''
                            INSERT INTO time_off_record (collaborator_id, date, record_type, days, amount_paid, rate_per_day, notes, origin, created_at, created_by)
                            SELECT collaborator_id, date, 'conversao', amount_days, amount_paid, COALESCE(rate_per_day, 65.0), COALESCE(notes, 'Conversão em dinheiro'), 'migrado', {now_func}, 'sistema'
                            FROM leave_conversion
                            WHERE NOT EXISTS (
                                SELECT 1 FROM time_off_record tor 
                                WHERE tor.collaborator_id = leave_conversion.collaborator_id 
                                AND tor.date = leave_conversion.date 
                                AND tor.record_type = 'conversao'
                                AND tor.days = leave_conversion.amount_days
                            )
                        '''))
                    
                    db.session.commit()
                    
                    # Após migração bem-sucedida, excluir tabelas antigas
                    try:
                        if 'hour_bank_entry' in tables:
                            db.session.execute(text('DROP TABLE IF EXISTS hour_bank_entry'))
                        if 'leave_credit' in tables:
                            db.session.execute(text('DROP TABLE IF EXISTS leave_credit'))
                        if 'leave_assignment' in tables:
                            db.session.execute(text('DROP TABLE IF EXISTS leave_assignment'))
                        if 'leave_conversion' in tables:
                            db.session.execute(text('DROP TABLE IF EXISTS leave_conversion'))
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        def _make_backup(retain_count: int = 20, min_interval_sec: int = 900, update_daily_snapshot: bool = True, force: bool = False):
            try:
                bdir = str(app.config.get('BACKUP_DIR') or '').strip()
                if not bdir:
                    return False
                os.makedirs(bdir, exist_ok=True)
                uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if isinstance(uri, str) and uri.startswith('sqlite:'):
                    src = str(app.config.get('DB_FILE_PATH') or '').strip()
                    if src and os.path.exists(src):
                        files_all = [
                            os.path.join(bdir, f) for f in os.listdir(bdir)
                            if isinstance(f, str) and f.lower().endswith('.sqlite')
                        ]
                        files_regular = sorted([
                            p for p in files_all
                            if os.path.basename(p).startswith('backup-') and not os.path.basename(p).startswith('backup-24h')
                        ], key=lambda p: os.path.getmtime(p), reverse=True)
                        if not force and files_regular:
                            try:
                                last_mt = os.path.getmtime(files_regular[0])
                            except Exception:
                                last_mt = 0
                            if last_mt and (time.time() - last_mt) < float(min_interval_sec):
                                if update_daily_snapshot:
                                    try:
                                        target = time.time() - 86400.0
                                        candidates = [(abs(os.path.getmtime(p) - target), p) for p in files_regular]
                                        candidates.sort(key=lambda t: t[0])
                                        if candidates:
                                            src24 = candidates[0][1]
                                            dst24 = os.path.join(bdir, 'backup-24h.sqlite')
                                            shutil.copy2(src24, dst24)
                                    except Exception:
                                        pass
                                return True
                        ts = time.strftime('%Y%m%d-%H%M%S')
                        dst = os.path.join(bdir, f'backup-{ts}.sqlite')
                        try:
                            import sqlite3
                            s_conn = sqlite3.connect(src)
                            d_conn = sqlite3.connect(dst)
                            try:
                                s_conn.backup(d_conn)
                            finally:
                                try:
                                    d_conn.close()
                                except Exception:
                                    pass
                                try:
                                    s_conn.close()
                                except Exception:
                                    pass
                        except Exception:
                            shutil.copy2(src, dst)
                        files_regular = sorted([
                            os.path.join(bdir, f) for f in os.listdir(bdir)
                            if isinstance(f, str) and f.lower().endswith('.sqlite') and f.startswith('backup-') and not f.startswith('backup-24h')
                        ], key=lambda p: os.path.getmtime(p), reverse=True)
                        for old in files_regular[retain_count:]:
                            try:
                                os.remove(old)
                            except Exception:
                                pass
                        if update_daily_snapshot:
                            try:
                                target = time.time() - 86400.0
                                files_regular = sorted([
                                    os.path.join(bdir, f) for f in os.listdir(bdir)
                                    if isinstance(f, str) and f.lower().endswith('.sqlite') and f.startswith('backup-') and not f.startswith('backup-24h')
                                ], key=lambda p: os.path.getmtime(p), reverse=True)
                                if files_regular:
                                    candidates = [(abs(os.path.getmtime(p) - target), p) for p in files_regular]
                                    candidates.sort(key=lambda t: t[0])
                                    src24 = candidates[0][1]
                                    dst24 = os.path.join(bdir, 'backup-24h.sqlite')
                                    shutil.copy2(src24, dst24)
                            except Exception:
                                pass
                        return True
                return False
            except Exception:
                return False

        def _start_backup_scheduler():
            enabled = os.getenv('DB_BACKUP_ENABLED', 'true').lower() == 'true'
            if not enabled:
                return
            def _loop():
                while True:
                    try:
                        with app.app_context():
                            _make_backup(retain_count=20, min_interval_sec=900, update_daily_snapshot=False, force=False)
                    except Exception:
                        pass
                    time.sleep(900)
            t = threading.Thread(target=_loop, daemon=True)
            t.start()

        def _start_daily_snapshot_scheduler():
            try:
                from datetime import datetime, timedelta
                from zoneinfo import ZoneInfo
            except Exception:
                return
            def _loop():
                while True:
                    try:
                        tz = ZoneInfo('America/Sao_Paulo')
                        now_dt = datetime.now(tz)
                        tomorrow = (now_dt + timedelta(days=1)).date()
                        next_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0, tzinfo=tz)
                        wait = (next_midnight - now_dt).total_seconds()
                        time.sleep(max(1, int(wait)))
                        with app.app_context():
                            ok = _make_backup(retain_count=20, min_interval_sec=0, update_daily_snapshot=False, force=True)
                            bdir = str(app.config.get('BACKUP_DIR') or '').strip()
                            if bdir:
                                try:
                                    files_regular = sorted([
                                        os.path.join(bdir, f) for f in os.listdir(bdir)
                                        if isinstance(f, str) and f.lower().endswith('.sqlite') and f.startswith('backup-') and not f.startswith('backup-24h')
                                    ], key=lambda p: os.path.getmtime(p), reverse=True)
                                    if files_regular:
                                        src = files_regular[0]
                                        dst = os.path.join(bdir, 'backup-24h.sqlite')
                                        shutil.copy2(src, dst)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            t = threading.Thread(target=_loop, daemon=True)
            t.start()

        setattr(app, 'perform_backup', _make_backup)
        _start_backup_scheduler()
        _start_daily_snapshot_scheduler()

        def _start_tempdata_scheduler():
            try:
                from datetime import datetime as _dt, timedelta as _td, date as _date
                from zoneinfo import ZoneInfo as _Zone
                from .models import Shift, TemporaryEntry
            except Exception:
                return
            def _loop():
                while True:
                    try:
                        tz = _Zone('America/Sao_Paulo')
                        with app.app_context():
                            today = _date.today()
                            # próximo domingo da semana corrente
                            domingo = today + _td(days=(6 - today.weekday()))
                            shifts = []
                            try:
                                shifts = Shift.query.filter(Shift.date == domingo).all()
                            except Exception:
                                shifts = []
                            for s in shifts:
                                cid = s.collaborator_id
                                if not cid:
                                    continue
                                try:
                                    is_5h = False
                                    if s.start_dt:
                                        try:
                                            is_5h = int(s.start_dt.astimezone(tz).hour) == 5
                                        except Exception:
                                            is_5h = False
                                    if (s.shift_type or '').lower().find('5h') >= 0:
                                        is_5h = True
                                    if is_5h:
                                        exists_b = TemporaryEntry.query.filter_by(kind='folga_hour_both', collaborator_id=cid, date=s.date).first()
                                        if not exists_b:
                                            tb = TemporaryEntry()
                                            tb.kind = 'folga_hour_both'
                                            tb.collaborator_id = cid
                                            tb.date = s.date
                                            tb.amount_days = 1
                                            tb.hours = 1.0
                                            tb.source = 'regra_domingo'
                                            tb.reason = 'Trabalho em domingo'
                                            db.session.add(tb)
                                    else:
                                        exists = TemporaryEntry.query.filter_by(kind='folga_credit', collaborator_id=cid, date=s.date).first()
                                        if not exists:
                                            te = TemporaryEntry()
                                            te.kind = 'folga_credit'
                                            te.collaborator_id = cid
                                            te.date = s.date
                                            te.amount_days = 1
                                            te.source = 'regra_domingo'
                                            te.reason = f'Trabalho em domingo {s.date.strftime("%d/%m/%Y")}'
                                            db.session.add(te)
                                except Exception:
                                    pass
                            try:
                                db.session.commit()
                            except Exception:
                                try:
                                    db.session.rollback()
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    time.sleep(3600)
            t = threading.Thread(target=_loop, daemon=True)
            t.start()

        _start_tempdata_scheduler()

        def _start_notif_scheduler():
            try:
                from datetime import datetime
                from zoneinfo import ZoneInfo
            except Exception:
                return
            try:
                target_hour = int(os.getenv('NOTIFICACOES_ENVIO_AUTOMATICO_HORA', '20'))
            except Exception:
                target_hour = 20
            def _loop():
                last_sent = None
                while True:
                    try:
                        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
                        if now.hour == target_hour and now.minute == 0:
                            d = now.date()
                            if last_sent != d:
                                try:
                                    from .services.notificacao_service import enviar_relatorio_diario
                                    with app.app_context():
                                        enviar_relatorio_diario('automatico', False)
                                except Exception:
                                    pass
                                last_sent = d
                                time.sleep(60)
                    except Exception:
                        pass
                    time.sleep(60)  # Otimizado: de 15s para 60s para reduzir uso de CPU
            t = threading.Thread(target=_loop, daemon=True)
            t.start()

        if notif_enabled:
            _start_notif_scheduler()
        
    @app.context_processor
    def inject_notif_flag():
        try:
            enabled = (os.getenv('NOTIFICACOES_ENABLED', 'false') or 'false').lower() == 'true'
        except Exception:
            enabled = False
        return {'notifications_enabled': enabled}
    
    @app.context_processor
    def inject_dev_flag():
        try:
            is_dev = bool(app.debug) or ((os.getenv('DEBUG', 'false') or 'false').lower() == 'true')
        except Exception:
            is_dev = False
        return {'is_dev': is_dev}
        
    try:
        import logging
        level_name = (os.getenv('FLASK_LOG_LEVEL') or '').strip().upper()
        if not level_name:
            level_name = 'DEBUG' if (os.getenv('DEBUG', 'false').lower() == 'true') else 'INFO'
        level = getattr(logging, level_name, logging.INFO)
        app.logger.setLevel(level)
        logging.getLogger('werkzeug').setLevel(level)
        app.config['LOG_BODY'] = (os.getenv('FLASK_LOG_BODY') or 'true').strip().lower() == 'true'
    except Exception:
        pass
    from flask import request, g
    @app.before_request
    def _http_log_req():
        try:
            p = request.path or ''
            if p.startswith('/static/'):
                return
            g._req_start = time.time()
            info = {}
            info['args'] = dict(request.args)
            if bool(app.config.get('LOG_BODY', False)):
                ct = (request.headers.get('Content-Type') or '').lower()
                body = None
                if 'application/json' in ct:
                    try:
                        j = request.get_json(silent=True)
                    except Exception:
                        j = None
                    if isinstance(j, dict):
                        masked = {}
                        sens = {'password','senha','new_password','confirmar_senha','token','authorization','secret'}
                        for k, v in j.items():
                            masked[k] = ('***' if (str(k).lower() in sens) else v)
                        body = masked
                    else:
                        body = j
                else:
                    try:
                        f = request.form.to_dict()
                    except Exception:
                        f = {}
                    sens = {'password','senha','new_password','confirmar_senha','token','authorization','secret'}
                    masked = {}
                    for k, v in (f or {}).items():
                        masked[k] = ('***' if (str(k).lower() in sens) else v)
                    body = masked
                info['body'] = body
            app.logger.info(f"REQ {request.method} {request.path} {info}")
        except Exception:
            pass
    @app.after_request
    def _http_log_resp(resp):
        try:
            p = request.path or ''
            if p.startswith('/static/'):
                return resp
            dur = 0.0
            try:
                dur = time.time() - getattr(g, '_req_start', time.time())
            except Exception:
                pass
            app.logger.info(f"RES {resp.status_code} {request.method} {request.path} dur={dur:.3f}s")
        except Exception:
            pass
        return resp
    def _on_exc(sender, exception, **extra):
        try:
            app.logger.exception(f"ERR {request.method} {request.path}: {exception}")
        except Exception:
            pass
    try:
        from flask import got_request_exception
        got_request_exception.connect(_on_exc, app)
    except Exception:
        pass
    
    return app
