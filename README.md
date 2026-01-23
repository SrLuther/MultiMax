# MultiMax

![Flask 2.3+](https://img.shields.io/badge/Flask-2.3+-0d6efd) ![Python 3.11+](https://img.shields.io/badge/Python-3.11+-0d6efd) ![Licença MIT](https://img.shields.io/badge/Licença-MIT-lightgrey) ![Versão 2.7.2](https://img.shields.io/badge/Versão-2.7.2-198754)

Plataforma web em Flask para gestão operacional com foco em rastreabilidade, controle de permissões e exportação de relatórios. Atual em produção em https://www.multimax.tec.br.

---

## Sumário

- Visão geral
- Funcionalidades-chave
- Stack técnica
- Requisitos
- Instalação rápida
- Configuração
- Modo de Manutenção
- Execução
- Módulos
- Testes
- Links úteis
- Licença

---

## Visão geral

- Controle de estoque com histórico de auditoria.
- Estoque de produção com previsão de uso e ajustes rastreáveis.
- Gestão de colaboradores/escalas e ciclos operacionais.
- Perfis de acesso: visualizador, operador, admin, DEV.

---

## Funcionalidades-chave

- **Estoque**: cadastro, entradas/saídas, alerta de mínimo e histórico.
- **Estoque de Produção**: previsão de uso, ajustes com motivo obrigatório, exportação em PDF (layout profissional).
- **Ciclos**: acompanhamento e fechamento periódico de horas/valores.
- **Colaboradores/Escalas**: gestão de pessoas e cronograma semanal.
- **Carnes/Receitas**: suporte a rastreabilidade e insumos.

Consulte o [CHANGELOG](CHANGELOG.md) para o detalhe das versões.

---

## Stack técnica

- Flask 2.3+, Flask-Login, Flask-SQLAlchemy
- SQLAlchemy 2.x
- ReportLab (PDFs), qrcode
- Banco: SQLite (dev) ou PostgreSQL (prod)

---

## Requisitos

- Python 3.11+
- pip e virtualenv
- Acesso a SQLite ou PostgreSQL

---

## Instalação rápida

```bash
git clone https://github.com/SrLuther/MultiMax.git
cd MultiMax
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python app.py
```

Ambientes:
- Produção: https://www.multimax.tec.br
- Desenvolvimento local: http://localhost:5000

---

## Configuração

Variáveis essenciais:

- `SQLALCHEMY_DATABASE_URI` — string do banco (ex.: `sqlite:///multimax.db` ou URL do PostgreSQL)
- `SECRET_KEY` — obrigatória em produção
- `SENHA_ADMIN`, `SENHA_OPERADOR` — credenciais iniciais
- `HOST`, `PORT` — caso queira alterar o endereço/porta
- `DEBUG` — desative em produção

Para produção, use um WSGI (ex.: Waitress ou gunicorn) e configure o banco PostgreSQL.

---

## Modo de Manutenção

O sistema possui um modo de manutenção que bloqueia completamente o acesso, exibindo uma página institucional elegante.

### Ativar

**Linux/macOS:**
```bash
./scripts/maintenance-mode.sh on
```

**Windows:**
```powershell
.\scripts\maintenance-mode.ps1 on
```

**Ou manualmente**, adicione ao arquivo `.env.txt` ou `.env`:
```env
MAINTENANCE_MODE=true
```

### Desativar

**Linux/macOS:**
```bash
./scripts/maintenance-mode.sh off
```

**Windows:**
```powershell
.\scripts\maintenance-mode.ps1 off
```

### Documentação completa

Para mais detalhes, consulte:
- [documentacao/MODO_MANUTENCAO.md](documentacao/MODO_MANUTENCAO.md)
- [documentacao/DOCKER_MAINTENANCE_MODE.md](documentacao/DOCKER_MAINTENANCE_MODE.md)

---

## Execução

- **Desenvolvimento**: `python app.py`
- **Produção (exemplo Waitress)**:

```bash
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

---

## Módulos

- `multimax/routes/estoque.py` — produtos, histórico e movimentações.
- `multimax/routes/estoque_producao.py` — estoque de produção, ajustes, PDF.
- `multimax/routes/ciclos.py` — ciclos e fechamentos periódicos.
- `multimax/routes/colaboradores.py` — colaboradores e escalas.
- `multimax/routes/carnes.py`, `multimax/routes/receitas.py` — carnes e receitas.

Templates em `templates/` e assets em `static/`.

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Links úteis

- Produção: https://www.multimax.tec.br
- Repositório: https://github.com/SrLuther/MultiMax
- Issues: https://github.com/SrLuther/MultiMax/issues
- Changelog: [CHANGELOG](CHANGELOG.md)

---

## Licença

MIT — veja [LICENSE](LICENSE).
