"""
Testes para rotas de autenticação.
"""
import pytest
from flask import url_for

from multimax import create_app, db
from multimax.models import User


@pytest.fixture
def app():
    """Cria uma instância da aplicação para testes."""
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
def test_user(app):
    """Cria um usuário de teste."""
    with app.app_context():
        from multimax.password_hash import generate_password_hash

        user = User()
        user.username = "testuser"
        user.name = "Test User"
        user.password_hash = generate_password_hash("testpass123")
        user.nivel = "operador"
        db.session.add(user)
        db.session.commit()
        return user


class TestLogin:
    """Testes para login."""

    def test_login_page_loads(self, client):
        """Testa se a página de login carrega."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"login" in response.data.lower()

    def test_login_success(self, client, test_user):
        """Testa login bem-sucedido."""
        response = client.post(
            "/login",
            data={"username": "testuser", "password": "testpass123", "action": "login"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_login_failure(self, client, test_user):
        """Testa login com credenciais inválidas."""
        response = client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpass", "action": "login"},
        )
        assert response.status_code == 200
        assert b"invalid" in response.data.lower() or b"inv" in response.data.lower()


class TestRegister:
    """Testes para registro de usuário."""

    def test_register_success(self, client, app):
        """Testa registro bem-sucedido."""
        with app.app_context():
            response = client.post(
                "/login",
                data={
                    "action": "register",
                    "username": "newuser",
                    "password": "newpass123",
                    "confirm_password": "newpass123",
                    "name": "New User",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Verifica se o usuário foi criado
            user = User.query.filter_by(username="newuser").first()
            assert user is not None
            assert user.nivel == "visualizador"

    def test_register_password_mismatch(self, client):
        """Testa registro com senhas diferentes."""
        response = client.post(
            "/login",
            data={
                "action": "register",
                "username": "newuser2",
                "password": "pass123",
                "confirm_password": "pass456",
                "name": "New User 2",
            },
        )
        assert response.status_code == 200
        assert b"coincid" in response.data.lower() or b"match" in response.data.lower()


class TestLogout:
    """Testes para logout."""

    def test_logout_requires_login(self, client):
        """Testa que logout requer login."""
        response = client.get("/logout", follow_redirects=True)
        assert response.status_code == 200

    def test_logout_success(self, client, test_user):
        """Testa logout bem-sucedido."""
        # Primeiro faz login
        client.post(
            "/login",
            data={"username": "testuser", "password": "testpass123", "action": "login"},
        )
        # Depois faz logout
        response = client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
