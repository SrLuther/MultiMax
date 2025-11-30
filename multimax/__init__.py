import os
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
    base_dir = os.path.dirname(os.path.dirname(__file__))
    _load_env(os.path.join(base_dir, '.env.txt'))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
    )
    db_path = os.path.join(base_dir, 'instance', 'estoque.db').replace('\\', '/')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_secreta_muito_forte_e_aleatoria')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PER_PAGE'] = 10

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes.auth import bp as auth_bp
    from .routes.estoque import bp as estoque_bp
    from .routes.cronograma import bp as cronograma_bp, setup_cleaning_tasks
    from .routes.exportacao import bp as exportacao_bp
    from .routes.usuarios import bp as usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(cronograma_bp)
    app.register_blueprint(exportacao_bp)
    app.register_blueprint(usuarios_bp)

    with app.app_context():
        db.create_all()
        if User.query.filter_by(username='admin').first() is None:
            admin = User(name='Administrador', username='admin', nivel='admin')
            from werkzeug.security import generate_password_hash
            admin.password_hash = generate_password_hash(os.getenv('SENHA_ADMIN', 'admin123'))
            db.session.add(admin)
            db.session.commit()
        if User.query.filter_by(username='operador').first() is None:
            operador = User(name='Operador Padrão', username='operador', nivel='operador')
            from werkzeug.security import generate_password_hash
            operador.password_hash = generate_password_hash(os.getenv('SENHA_OPERADOR', 'op123'))
            db.session.add(operador)
            db.session.commit()
        setup_cleaning_tasks()

    return app
