# Testes do MultiMax

Este diretório contém a suíte de testes do projeto MultiMax.

## Estrutura de Testes

```
tests/
├── __init__.py
├── README.md
├── test_example.py          # Testes de exemplo
├── test_models.py           # Testes para modelos (User, Produto, Historico)
├── test_auth.py             # Testes para autenticação (login, registro, logout)
├── test_estoque.py          # Testes para rotas de estoque
└── test_password_hash.py   # Testes para funções de hash de senha
```

## Como Executar os Testes

### Executar todos os testes

```bash
pytest
```

### Executar com cobertura

```bash
pytest --cov=multimax --cov-report=html --cov-report=term-missing
```

### Executar um arquivo específico

```bash
pytest tests/test_models.py
```

### Executar uma classe específica

```bash
pytest tests/test_models.py::TestUser
```

### Executar um teste específico

```bash
pytest tests/test_models.py::TestUser::test_user_creation
```

### Executar com verbosidade

```bash
pytest -v
```

### Executar com saída detalhada

```bash
pytest -vv
```

## Cobertura de Código

O projeto tem como meta **mínima de 80% de cobertura de código**.

### Verificar cobertura

```bash
pytest --cov=multimax --cov-report=html --cov-report=term-missing --cov-fail-under=80
```

### Visualizar relatório HTML

Após executar os testes com `--cov-report=html`, abra o arquivo `htmlcov/index.html` no navegador.

## Adicionando Novos Testes

### Estrutura de um Teste

```python
import pytest
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

def test_exemplo(app, client):
    """Exemplo de teste."""
    response = client.get("/")
    assert response.status_code == 200
```

### Convenções

1. **Nomes de arquivos**: Começam com `test_` (ex: `test_models.py`)
2. **Nomes de funções**: Começam com `test_` (ex: `test_user_creation`)
3. **Nomes de classes**: Começam com `Test` (ex: `TestUser`)
4. **Fixtures**: Colocadas no início do arquivo ou em `conftest.py`

### Fixtures Úteis

- `app`: Aplicação Flask configurada para testes
- `client`: Cliente de teste HTTP
- `test_user`: Usuário de teste pré-criado
- `test_produto`: Produto de teste pré-criado
- `logged_in_client`: Cliente com usuário já autenticado

### Exemplo de Teste de Rota

```python
def test_rota_requer_login(client):
    """Testa que uma rota requer login."""
    response = client.get("/estoque", follow_redirects=True)
    assert response.status_code == 200
    # Verifica redirecionamento para login
    assert b"login" in response.data.lower()
```

### Exemplo de Teste de Modelo

```python
def test_modelo_criacao(app):
    """Testa criação de modelo."""
    with app.app_context():
        user = User()
        user.username = "testuser"
        user.name = "Test User"
        db.session.add(user)
        db.session.commit()
        
        assert User.query.filter_by(username="testuser").first() is not None
```

## Mocks e Stubs

Para testar funcionalidades que dependem de serviços externos, use `pytest-mock`:

```python
from unittest.mock import Mock, patch

def test_com_mock(mocker):
    """Exemplo de teste com mock."""
    mock_request = mocker.patch('requests.get')
    mock_request.return_value.json.return_value = {"status": "ok"}
    
    # Seu código que usa requests.get
    # ...
    
    mock_request.assert_called_once()
```

## Integração Contínua

Os testes são executados automaticamente no CI/CD através do GitHub Actions (`.github/workflows/ci.yml`).

### Requisitos do CI

- Todos os testes devem passar
- Cobertura mínima de 80%
- Sem avisos críticos do flake8
- Sem vulnerabilidades de segurança (bandit, safety)

## Dependências de Teste

As dependências de teste estão em `requirements-dev.txt`:

- `pytest>=7.4.4`
- `pytest-cov>=4.1.0`
- `pytest-mock>=3.12.0`

## Troubleshooting

### Erro: "No module named 'multimax'"

Certifique-se de estar no diretório raiz do projeto e que o ambiente virtual está ativado.

### Erro: "Database is locked"

Isso pode acontecer com SQLite em memória. Tente executar os testes um de cada vez ou use um banco de dados temporário.

### Testes falhando após mudanças no código

Execute `pytest --tb=short` para ver um traceback mais curto e identificar o problema mais rapidamente.

## Recursos Adicionais

- [Documentação do pytest](https://docs.pytest.org/)
- [Documentação do pytest-cov](https://pytest-cov.readthedocs.io/)
- [Documentação do Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
