import os
import sys
from flask import Flask
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

def create_app():
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
    _load_env(os.path.join(base_dir, '.env.txt'))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )
    data_dir = None
    if os.name == 'nt':
        localapp = os.getenv('LOCALAPPDATA')
        if localapp:
            data_dir = os.path.join(localapp, 'MultiMax')
    if not data_dir:
        home = os.path.expanduser('~')
        data_dir = os.path.join(home, '.multimax')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'estoque.db').replace('\\', '/')
    uri_env = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if uri_env and uri_env.startswith('postgresql://'):
        uri_env = 'postgresql+psycopg://' + uri_env.split('://', 1)[1]
    if uri_env and uri_env.startswith('postgres://'):
        uri_env = 'postgresql+psycopg://' + uri_env.split('://', 1)[1]
    try:
        s = uri_env or ''
        if s and ('.supabase.co' in s) and ('@' in s):
            pre, post = s.split('@', 1)
            rest = post.split('/', 1)[1] if '/' in post else ''
            hostport = 'aws-1-sa-east-1.pooler.supabase.com:5432'
            s = pre + '@' + hostport + ('/' + rest if rest else '')
        if s and ('sslmode=' not in s):
            s = s + ('&sslmode=require' if '?' in s else '?sslmode=require')
        uri_env = s or uri_env
    except Exception:
        pass
    app.config['SQLALCHEMY_DATABASE_URI'] = uri_env if uri_env else ('sqlite:///' + db_path)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_secreta_muito_forte_e_aleatoria')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PER_PAGE'] = 10

    db.init_app(app)
    login_manager.init_app(app)
    setattr(login_manager, 'login_view', 'auth.login')
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes.auth import bp as auth_bp
    from .routes.home import bp as home_bp
    from .routes.estoque import bp as estoque_bp
    from .routes.cronograma import bp as cronograma_bp, setup_cleaning_tasks
    from .routes.exportacao import bp as exportacao_bp
    from .routes.usuarios import bp as usuarios_bp
    from .routes.carnes import bp as carnes_bp
    from .routes.colaboradores import bp as colaboradores_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(cronograma_bp)
    app.register_blueprint(exportacao_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carnes_bp)
    app.register_blueprint(colaboradores_bp)

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

    @app.context_processor
    def inject_notifications():
        try:
            from .models import Produto, CleaningTask, NotificationRead
            from datetime import date
            from flask import url_for, request
            from flask_login import current_user
            if not current_user.is_authenticated:
                return {'notif_items': [], 'notif_count': 0}
            nf = request.args.get('nf', '').strip()  # filtro: '', 'estoque', 'limpeza'
            cat = request.args.get('cat', '').strip().upper()  # categoria estoque: CX/PC/VA/AV
            today = date.today()
            low_stock = Produto.query.filter(Produto.quantidade <= Produto.estoque_minimo).order_by(Produto.nome.asc()).all()
            overdue = CleaningTask.query.filter(CleaningTask.proxima_data < today).order_by(CleaningTask.proxima_data.asc()).all()
            reads = NotificationRead.query.filter_by(user_id=current_user.id).all()
            read_set = {(r.tipo, r.ref_id) for r in reads}
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
        try:
            import json
            from urllib.request import Request, urlopen
            owner = os.getenv('GITHUB_OWNER', 'SrLuther')
            repo = os.getenv('GITHUB_REPO', 'MultiMax')
            req = Request(f'https://api.github.com/repos/{owner}/{repo}/releases/latest', headers={'User-Agent': 'MultiMax-App'})
            with urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                tag = data.get('tag_name')
                if tag:
                    return tag
        except Exception:
            pass
        try:
            import json
            from urllib.request import Request, urlopen
            owner = os.getenv('GITHUB_OWNER', 'SrLuther')
            repo = os.getenv('GITHUB_REPO', 'MultiMax')
            req = Request(f'https://api.github.com/repos/{owner}/{repo}/tags', headers={'User-Agent': 'MultiMax-App'})
            with urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if isinstance(data, list) and data:
                    name = data[0].get('name')
                    if name:
                        return name
        except Exception:
            pass
        try:
            import subprocess
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
            r = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], cwd=base_dir, capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout.strip()
            r2 = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=base_dir, capture_output=True, text=True)
            if r2.returncode == 0:
                return r2.stdout.strip()
        except Exception:
            pass
        v = os.getenv('APP_VERSION')
        if v:
            return v
        return 'dev'

    @app.context_processor
    def inject_version():
        raw = _get_version()
        v = raw.lstrip('vV') if isinstance(raw, str) else raw
        return {'git_version': v}

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
        db.create_all()
        if not is_sqlite:
            try:
                from sqlalchemy import text
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE TEXT'))
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        if not is_sqlite:
            try:
                from sqlalchemy import text
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
                    'shift','leave_credit','hour_bank_entry','user'
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
        if User.query.filter_by(username='admin').first() is None:
            admin = User()
            admin.name = 'Administrador'
            admin.username = 'admin'
            admin.nivel = 'admin'
            from werkzeug.security import generate_password_hash
            admin.password_hash = generate_password_hash(os.getenv('SENHA_ADMIN', 'admin123'))
            db.session.add(admin)
            db.session.commit()
        if User.query.filter_by(username='operador').first() is None:
            operador = User()
            operador.name = 'Operador Padrão'
            operador.username = 'operador'
            operador.nivel = 'operador'
            from werkzeug.security import generate_password_hash
            operador.password_hash = generate_password_hash(os.getenv('SENHA_OPERADOR', 'op123'))
            db.session.add(operador)
            db.session.commit()
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
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

    return app
