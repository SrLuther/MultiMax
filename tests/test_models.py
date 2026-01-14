"""
Testes unitários para os modelos do MultiMax.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from multimax import create_app, db
from multimax.models import Historico, Produto, User


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
        user = User()
        user.username = "testuser"
        user.name = "Test User"
        user.password_hash = "test_hash"
        user.nivel = "operador"
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_produto(app):
    """Cria um produto de teste."""
    with app.app_context():
        produto = Produto()
        produto.codigo = "AV-0001"
        produto.nome = "Produto Teste"
        produto.quantidade = 10
        produto.estoque_minimo = 5
        produto.preco_custo = 10.50
        produto.preco_venda = 15.00
        db.session.add(produto)
        db.session.commit()
        return produto


class TestUser:
    """Testes para o modelo User."""

    def test_user_creation(self, app, test_user):
        """Testa criação de usuário."""
        with app.app_context():
            assert test_user.username == "testuser"
            assert test_user.name == "Test User"
            assert test_user.nivel == "operador"

    def test_user_query(self, app, test_user):
        """Testa consulta de usuário."""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user is not None
            assert user.id == test_user.id


class TestProduto:
    """Testes para o modelo Produto."""

    def test_produto_creation(self, app, test_produto):
        """Testa criação de produto."""
        with app.app_context():
            assert test_produto.codigo == "AV-0001"
            assert test_produto.nome == "Produto Teste"
            assert test_produto.quantidade == 10
            assert test_produto.estoque_minimo == 5

    def test_produto_update(self, app, test_produto):
        """Testa atualização de produto."""
        with app.app_context():
            produto = Produto.query.get(test_produto.id)
            produto.quantidade = 20
            db.session.commit()
            updated = Produto.query.get(test_produto.id)
            assert updated.quantidade == 20

    def test_produto_delete(self, app, test_produto):
        """Testa exclusão de produto."""
        with app.app_context():
            produto_id = test_produto.id
            db.session.delete(test_produto)
            db.session.commit()
            deleted = Produto.query.get(produto_id)
            assert deleted is None


class TestHistorico:
    """Testes para o modelo Historico."""

    def test_historico_creation(self, app, test_produto):
        """Testa criação de histórico."""
        with app.app_context():
            hist = Historico()
            hist.product_id = test_produto.id
            hist.product_name = test_produto.nome
            hist.action = "entrada"
            hist.quantidade = 5
            hist.details = "Teste de entrada"
            hist.usuario = "testuser"
            db.session.add(hist)
            db.session.commit()

            historico = Historico.query.filter_by(product_id=test_produto.id).first()
            assert historico is not None
            assert historico.action == "entrada"
            assert historico.quantidade == 5

    def test_historico_relationship(self, app, test_produto):
        """Testa relacionamento entre Produto e Historico."""
        with app.app_context():
            hist = Historico()
            hist.product_id = test_produto.id
            hist.product_name = test_produto.nome
            hist.action = "saida"
            hist.quantidade = 2
            hist.usuario = "testuser"
            db.session.add(hist)
            db.session.commit()

            produto = Produto.query.get(test_produto.id)
            assert len(produto.historicos) > 0
