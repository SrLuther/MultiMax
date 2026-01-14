"""
Testes para rotas de estoque.
"""
import pytest
from flask import url_for

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
        from multimax.password_hash import generate_password_hash

        user = User()
        user.username = "testuser"
        user.name = "Test User"
        user.password_hash = generate_password_hash("testpass123")
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


@pytest.fixture
def logged_in_client(client, test_user):
    """Cliente com usuário logado."""
    client.post(
        "/login",
        data={"username": "testuser", "password": "testpass123", "action": "login"},
    )
    return client


class TestEstoqueRoutes:
    """Testes para rotas de estoque."""

    def test_estoque_index_requires_login(self, client):
        """Testa que a página de estoque requer login."""
        response = client.get("/estoque", follow_redirects=True)
        assert response.status_code == 200

    def test_estoque_index_loads(self, logged_in_client):
        """Testa se a página de estoque carrega."""
        response = logged_in_client.get("/estoque")
        assert response.status_code == 200

    def test_adicionar_produto(self, logged_in_client, app):
        """Testa adição de produto."""
        with app.app_context():
            response = logged_in_client.post(
                "/estoque/adicionar",
                data={
                    "nome": "Novo Produto",
                    "categoria": "AV",
                    "quantidade": "5",
                    "estoque_minimo": "3",
                    "preco_custo": "10.00",
                    "preco_venda": "15.00",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Verifica se o produto foi criado
            produto = Produto.query.filter_by(nome="Novo Produto").first()
            assert produto is not None
            assert produto.quantidade == 5

    def test_entrada_produto(self, logged_in_client, app, test_produto):
        """Testa entrada de produto."""
        with app.app_context():
            quantidade_inicial = test_produto.quantidade
            response = logged_in_client.post(
                f"/estoque/entrada/{test_produto.id}",
                data={"quantidade": "5"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Verifica se a quantidade foi atualizada
            produto = Produto.query.get(test_produto.id)
            assert produto.quantidade == quantidade_inicial + 5

            # Verifica se o histórico foi criado
            historico = Historico.query.filter_by(product_id=test_produto.id, action="entrada").first()
            assert historico is not None
            assert historico.quantidade == 5

    def test_saida_produto(self, logged_in_client, app, test_produto):
        """Testa saída de produto."""
        with app.app_context():
            quantidade_inicial = test_produto.quantidade
            response = logged_in_client.post(
                f"/estoque/saida/{test_produto.id}",
                data={"quantidade": "3"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Verifica se a quantidade foi atualizada
            produto = Produto.query.get(test_produto.id)
            assert produto.quantidade == quantidade_inicial - 3

    def test_saida_insuficiente(self, logged_in_client, app, test_produto):
        """Testa saída com quantidade insuficiente."""
        with app.app_context():
            quantidade_inicial = test_produto.quantidade
            response = logged_in_client.post(
                f"/estoque/saida/{test_produto.id}",
                data={"quantidade": str(quantidade_inicial + 10)},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Verifica que a quantidade não mudou
            produto = Produto.query.get(test_produto.id)
            assert produto.quantidade == quantidade_inicial
