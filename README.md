<p align="center">
  <img src="https://raw.githubusercontent.com/SrLuther/MultiMax/main/static/icons/logo-user.png" height="140"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Flask-198754?style=for-the-badge&logo=flask&logoColor=white&labelColor=1a1d1f&color=198754" alt="Flask Badge"/>
  <img src="https://img.shields.io/badge/Python-3.10+-1a1d1f?style=for-the-badge&logo=python&logoColor=yellow&labelColor=198754&color=1a1d1f" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-198754?style=for-the-badge&labelColor=1a1d1f&color=198754" alt="Status Badge"/>
</p>

# 🌟 MultiMax — Plataforma Integrada de Gestão

---

## 🚀 Sobre o MultiMax

O **MultiMax** é uma plataforma **web moderna e premium** de gestão interna, desenvolvida com **Flask**, com **interface responsiva**, **gradientes neon** e painéis otimizados para produtividade.  

Funcionalidades principais:  
- ✔ Gestão de Estoque  
- ✔ Cronograma de Limpeza  
- ✔ Gestão de Colaboradores  
- ✔ Backups Automáticos  
- ✔ Administração Completa do Banco de Dados  
- ✔ Sistema de Login com Níveis  
- ✔ Painéis Modernos com Gradientes e Neon  

---

## ⚡ Módulos Principais

### 🗃️ Estoque
- Interface visual em tempo real com efeitos neon  
- Organização por categorias e tipo  
- Quantidades sem conferência física  
- Histórico detalhado de movimentações  
- Filtros inteligentes  

### 🧼 Cronograma de Limpeza
- Planejamento quinzenal automático  
- Histórico completo das ações realizadas  
- Filtros por período  
- Regras inteligentes (evita agendar dias 1–4)  
- Cards dinâmicos com cores neon  

### 👥 Colaboradores
- Escalas personalizadas  
- Perfis e credenciais com níveis  
- Atribuição de permissões por função  

### 🛢️ Banco de Dados & Backups
- Backup automático a cada hora  
- Mantém os 10 backups mais recentes  
- Snapshot pré-restauração  
- Restaurar backup ou snapshot com 1 clique  
- Painel administrativo seguro  

---

## 🌈 Tecnologias Utilizadas

- **Python 3.10+**  
- **Flask + Login Manager**  
- **SQLAlchemy**  
- **Bootstrap 5.3** (customização neon)  
- **Waitress** (produção Windows)  
- **FontAwesome**  
- **Matplotlib / ReportLab**  
- **SQLite / PostgreSQL**  

---

## 📦 Instalação e Execução (Bloco único)

- git clone https://github.com/SrLuther/MultiMax.git
- cd MultiMax
- pip install -r requirements.txt
- python -m venv .venv
- .\.venv\Scripts\activate   # Windows
- source .venv/bin/activate   # Linux/macOS
- start_local.cmd
- python app.py
- Acesse: ➡️ [MultiMax](https://multimax.tec.br/)

---

##  ⚙️ Configuração de Variáveis de Ambiente
- Variável	Exemplo	Descrição
- HOST	0.0.0.0	Endereço do servidor
- PORT	5000	Porta da aplicação
- DEBUG	True / False	Ativa modo debug
- SQLALCHEMY_DATABASE_URI	sqlite:///multimax.db	Conexão com o banco
- SENHA_ADMIN	Senha do administrador
- SENHA_OPERADOR	Senha do operador
- DB_BACKUP_ENABLED	True / False	Ativa backups automáticos
- KEEPALIVE_ENABLED	True / False	Ativa ping keepalive
- KEEPALIVE_URL	http://localhost:5000	URL do ping
- KEEPALIVE_INTERVAL	300	Intervalo em segundos

---

## 💾 Backups & Snapshots
- Backup automático a cada hora

- Mantém os 10 mais recentes

- Snapshot pré-restauração

- Restaurar backup ou snapshot com 1 clique

---

## 🔐 Login Padrão
- Usuários: admin e operador

- Senhas definidas pelas variáveis de ambiente ou na primeira execução

---

## 🖼️ Interface Premium (Exemplo)
<p align="center"> <img src="https://raw.githubusercontent.com/SrLuther/MultiMax/main/static/icons/logo-user.png" width="400"/> </p>
📄 Licença
MIT License
