# MultiMax

![Flask 2.3+](https://img.shields.io/badge/Flask-2.3+-blue) ![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue) ![Licenca MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-lightgrey) ![Versao 2.7.2](https://img.shields.io/badge/Vers%C3%A3o-2.7.2-green)

Plataforma web em Flask para gestão operacional (estoque, produção e rotinas internas). Foco em rastreabilidade, controle de permissões e relatórios exportáveis.

---

## Visão geral

- **Estoque**: cadastro de produtos, entradas/saídas e histórico com auditoria.
- **Estoque de Produção**: previsão de uso, ajustes com motivo obrigatório e exportação em PDF.
- **Colaboradores/Escalas**: gestão de pessoas e cronograma semanal.
- **Ciclos**: acompanhamento e fechamento periódico de horas/valores.
- **Autenticação**: níveis de acesso (visualizador, operador, admin, DEV).

Consulte o [CHANGELOG](CHANGELOG.md) para detalhes da versão atual.

---

## Requisitos

- Python 3.11+
- Pip e virtualenv
- Banco SQLite (dev) ou PostgreSQL (prod)

---

## Instalação e execução

```bash
git clone https://github.com/SrLuther/MultiMax.git
cd MultiMax
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python app.py
```

Produção: https://www.multimax.tec.br. Desenvolvimento local: http://localhost:5000.

---

## Configuração mínima

Defina variáveis de ambiente conforme necessidade:

- `SQLALCHEMY_DATABASE_URI` (ex.: `sqlite:///multimax.db` ou string do PostgreSQL)
- `SECRET_KEY` (obrigatória em produção)
- `SENHA_ADMIN` e `SENHA_OPERADOR` (credenciais iniciais)
- `HOST` / `PORT` (se desejar alterar o host/porta padrão)

Para produção, configure também servidor WSGI (ex.: Waitress ou gunicorn) e desative `DEBUG`.

---

## Principais módulos

- `multimax/routes/estoque.py`: gestão de produtos, histórico e movimentações.
- `multimax/routes/estoque_producao.py`: estoque de produção, ajustes e PDF.
- `multimax/routes/ciclos.py`: ciclos e fechamentos periódicos.
- `multimax/routes/colaboradores.py`: colaboradores e escalas.
- `multimax/routes/carnes.py` e `multimax/routes/receitas.py`: controle de carnes e receitas.

Templates estão em `templates/` e assets em `static/`.

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Contribuição

1. Crie uma branch: `git checkout -b feature/sua-feature`
2. Faça commits claros (Conventional Commits são bem-vindos)
3. Abra um PR descrevendo mudanças e passos de teste

Issues e sugestões: https://github.com/SrLuther/MultiMax/issues

---

## Licença

MIT. Veja [LICENSE](LICENSE).
