"""
Configuração compartilhada para testes pytest.
"""
import os

import pytest

# Configurar variáveis de ambiente para testes
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")


@pytest.fixture(scope="session")
def app():
    """Cria uma instância da aplicação para testes (session scope)."""
    from multimax import create_app, db

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Cria um cliente de teste."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Cria uma sessão de banco de dados para testes."""
    from multimax import db

    with app.app_context():
        yield db.session
        db.session.rollback()
