<p align="center">
  <img src="https://raw.githubusercontent.com/SrLuther/MultiMax/main/static/icons/logo-user.png" height="140"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Flask-198754?style=for-the-badge&logo=flask&logoColor=white&labelColor=1a1d1f&color=198754" alt="Flask Badge"/>
  <img src="https://img.shields.io/badge/Python-3.11+-1a1d1f?style=for-the-badge&logo=python&logoColor=yellow&labelColor=198754&color=1a1d1f" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/Status-Estável-198754?style=for-the-badge&labelColor=1a1d1f&color=198754" alt="Status Badge"/>
  <img src="https://img.shields.io/badge/Licença-MIT-1a1d1f?style=for-the-badge&labelColor=198754&color=1a1d1f" alt="License Badge"/>
</p>

<p align="center">
  <img src="https://github.com/SrLuther/MultiMax/workflows/CI/badge.svg" alt="CI Status"/>
  <img src="https://img.shields.io/codecov/c/github/SrLuther/MultiMax?label=coverage" alt="Code Coverage"/>
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black"/>
  <img src="https://img.shields.io/badge/security-bandit-yellow.svg" alt="Security: Bandit"/>
  <img src="https://img.shields.io/badge/types-mypy-blue.svg" alt="Type Checking: mypy"/>
</p>

# MultiMax — Plataforma Integrada de Gestão Operacional

MultiMax é um sistema web completo para gestão operacional em ambientes produtivos e pré‑produtivos. Foca em previsibilidade, manutenibilidade e segurança, cobrindo jornada de colaboradores (horas/folgas), escalas, limpeza, compras, temperatura, relatórios e administração.

—

## 1. Descrição e Objetivos

- Centralizar rotinas operacionais em um único produto de fácil uso.
- Garantir rastreabilidade (histórico, logs, exportações) e controle de acesso por níveis.
- Oferecer UX responsiva, com componentes consistentes e performance estável em Windows.
- Facilitar auditoria e tomada de decisão com dashboards, KPIs e relatórios exportáveis.

—

## 2. Funcionalidades Principais e Benefícios

- Jornada Unificada: registros de horas e folgas, filtros por período/colaborador/tipo, ordenação múltipla, paginação e histórico de alterações. Exportação CSV/XLSX.
- Folgas/Férias/Atestados: cadastro de uso/crédito de folgas (inclui conversão em R$), períodos de férias com cálculo de dias, atestados com foto, motivo e CID.
- Escalas Semanais: visão por colaborador e dia, destaque de “hoje”, contagem de horas e detecção de conflitos com instruções de resolução.
- Cronograma de Limpeza: checklist dinâmico por tipo, histórico de tarefas, conclusão com grids responsivos e calendário.
- Compras/Fornecedores/Produtos: pedidos e itens integrados a fornecedores e catálogo de produtos.
- Temperatura: registro por local com fotos e gestão de locais.
- Relatórios e Exportações: consolidados em Excel/CSV, seleção por período e colaborador.
- Administração e Segurança: níveis (admin/operador), logs seguros (mascaramento de dados sensíveis), backups agendados.
- PWA (manifest): atalhos para áreas críticas (Estoque, Cronograma e Relatórios).

Benefícios:
- Previsibilidade operacional, menos erros humanos e maior produtividade.
- Evidências rápidas para auditoria e melhoria contínua.
- Escalabilidade simples em Windows/Waitress.

—

## 3. Requisitos Técnicos e Dependências

Versão de Python: 3.10+

Dependências principais (requirements.txt):

```
Flask>=2.3.0
Flask-SQLAlchemy>=3.0.0
Flask-Login>=0.6.2
SQLAlchemy>=2.0.0
alembic>=1.13.0
psycopg[binary]>=3.1
reportlab>=4.0.0
matplotlib>=3.8.0
Pillow>=10.0.0
qrcode[pil]>=7.4.2
openpyxl>=3.1.2
waitress>=2.1.2
requests>=2.31.0
psutil>=5.9.8
```

Ferramentas/Configurações:
- Bootstrap 5.3 (UI), Bootstrap Icons.
- pyrightconfig.json (type checking: básico, opcional).
- Banco: SQLite e/ou PostgreSQL via SQLAlchemy.

—

## 4. Instalação e Configuração

Instalação (Windows/Linux/macOS):

```bash
git clone https://github.com/SrLuther/MultiMax.git
cd MultiMax
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
```

Variáveis de Ambiente (exemplos):

| Variável | Exemplo | Descrição |
|---------|---------|-----------|
| HOST | 0.0.0.0 | Endereço do servidor |
| PORT | 5000 | Porta da aplicação |
| DEBUG | True/False | Modo debug |
| SQLALCHEMY_DATABASE_URI | sqlite:///multimax.db | Conexão com banco |
| SENHA_ADMIN | ******** | Senha do administrador |
| SENHA_OPERADOR | ******** | Senha do operador |
| DB_BACKUP_ENABLED | True/False | Ativa backups automáticos |
| KEEPALIVE_ENABLED | True/False | Ativa ping keepalive |
| KEEPALIVE_URL | http://localhost:5000 | URL do ping |
| KEEPALIVE_INTERVAL | 300 | Intervalo (s) |

Execução local:

```bash
python app.py
# ou Waitress (produção Windows)
# waitress-serve --host=0.0.0.0 --port=5000 app:app
```

Versão da aplicação:
- Resolvida dinamicamente via APP_VERSION, tag Git ou commit; fallback: 2.1.0.0.

—

## 5. Guia de Uso (Exemplos)

Navegação (web):
- Jornada: filtros por colaborador/tipo/período; ordenação e exportação.
- Folgas/Férias/Atestados: cadastro e listagens com paginação.
- Escala: visão semanal com conflitos.
- Cronograma: tarefas e checklist.
- Relatórios: geração e download.

Exportar jornada (CSV) por período:

```bash
curl -L "http://localhost:5000/jornada/export?colaborador=123&inicio=2025-01-01&fim=2025-01-31&fmt=csv" -o jornada.csv
```

Exportar jornada (Excel) em um dia específico:

```bash
curl -L "http://localhost:5000/jornada/export?colaborador=123&inicio=2025-01-15&fim=2025-01-15&fmt=xlsx" -o jornada.xlsx
```

Verificar feriados/validação de data (exemplo client-side integra endpoint):

```javascript
fetch("/jornada/is_holiday?date=2025-01-15").then(r=>r.json()).then(j=>{
  if (j.holiday) console.log("Feriado:", j.name);
});
```

—

## 6. Contribuição e Código de Conduta

Contribuição:
- Abra uma issue descrevendo claramente a proposta/bug.
- Fork, crie branch feature/xxx ou fix/xxx.
- Siga padrões existentes (UI, rotas, modelos) e mudanças incrementais.
- Evite alterar lógica de negócio sem pedido explícito.
- Envie PR com descrição, escopo e testes/validações.

Código de Conduta:
- Respeito e colaboração.
- Sem exposição de segredos/credenciais.
- Revisões focadas em manutenibilidade e previsibilidade.

—

## 7. Licença

MIT License — veja o arquivo LICENSE ou a seção de Licença neste README.

—

## 8. Contato e Suporte

- Site: https://multimax.tec.br/
- Suporte: abra uma issue neste repositório ou contate via site.
- Status/Versão: exibidos na interface e resolvidos automaticamente pelo sistema.

—

## 9. Tecnologias (Resumo)

- Backend: Flask, Flask‑Login, SQLAlchemy.
- Frontend: Jinja + Bootstrap 5.3, Bootstrap Icons.
- Produção: Waitress (Windows).
- Utilitários: openpyxl, reportlab, matplotlib, Pillow, qrcode.

—

## 10. Notas de Arquitetura

- Logs de requisição com mascaramento de campos sensíveis.
- Injeção de versão por contexto (tag/commit/APP_VERSION).
- PWA com manifest e atalhos para áreas-chave.

## 11. Qualidade e Segurança

O projeto MultiMax implementa uma suíte completa de ferramentas de qualidade e segurança:

### Ferramentas de Qualidade

- **Black**: Formatação automática de código Python
- **isort**: Organização de imports
- **flake8**: Linting e verificação de estilo
- **mypy**: Verificação estática de tipos
- **pytest**: Framework de testes com cobertura mínima de 80%
- **pytest-cov**: Geração de relatórios de cobertura (HTML, XML, terminal)

### Ferramentas de Segurança

- **bandit**: Análise de segurança do código Python
- **safety**: Verificação de vulnerabilidades em dependências
- **ESLint/Prettier**: Análise de código JavaScript/TypeScript
- **JavaScript Safety Check**: Verificação customizada de padrões inseguros em templates

### CI/CD

O pipeline CI/CD (`.github/workflows/ci.yml`) executa automaticamente:

1. Pre-commit hooks (formatação, linting)
2. Verificação de tipos (mypy)
3. Testes com cobertura (pytest)
4. Análise de segurança (bandit, safety)
5. Verificação de JavaScript (ESLint, safety check)

### Testes

Consulte `tests/README.md` para informações detalhadas sobre como executar e adicionar testes.

### Cobertura

- Meta mínima: **90% global**, **100% para funções críticas**
- Relatórios gerados em: terminal, XML (CI/CD), HTML (visualização)
- Cobertura de branches incluída para garantir testes de todos os caminhos de código
