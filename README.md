🌐 <img src="https://raw.githubusercontent.com/SrLuther/MultiMax/main/static/icons/logo-user.png" height="90"/>
MultiMax — Plataforma Integrada de Gestão
<div align="center"> <img width="650" src="https://img.shields.io/badge/Flask%20Framework-198754?style=for-the-badge&logo=flask&logoColor=white&labelColor=1a1d1f&color=198754&cacheSeconds=1"/> <img width="650" src="https://img.shields.io/badge/Python-3.10+-1a1d1f?style=for-the-badge&logo=python&logoColor=yellow&cacheSeconds=1"/> <img width="650" src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-198754?style=for-the-badge&logoColor=white&labelColor=1a1d1f&cacheSeconds=1"/> </div>
<style> /* EFEITO NEON NO README (GitHub permite estilo inline limitado) */ img[src*="badge"] { filter: drop-shadow(0 0 6px #00ff95); } </style> <div align="center">
🌈 Gradiente Oficial MultiMax

linear-gradient(135deg, #198754, #12c27d, #0aa56a)

💡 Borda Neon Premium

shadow: 0 0 12px #00ff9d

</div>
✨ Identidade Visual Premium MultiMax
Elemento	Cor	Hex
Primário (Neon Premium)	Verde vibrante	#1EFF99
Secundário (Verde Profundo)	Verde escuro	#157347
Cinza Elegante	Fundo e contraste	#1a1d1f
Cinza Claro	Superfícies	#f4f4f5
Fonte Oficial	Ubuntu	300 / 400 / 500 / 700
🔥 Destaque Visual (Mostre isso no GitHub)

💚 Todo o MultiMax segue esse estilo visual elegante com neon suave, contrastes premium e tipografia Ubuntu, inclusive a tela de login animada que você pediu — dando identidade profissional ao sistema.

🚀 O que é o MultiMax?

O MultiMax é uma plataforma web moderna de gestão interna desenvolvida com Flask, projetada para unificar processos administrativos essenciais:

✔ Estoque
✔ Cronograma de limpeza
✔ Gestão de colaboradores
✔ Backups automáticos
✔ Administração completa do banco de dados
✔ Sistema de login com níveis
✔ Painéis modernos e responsivos
✔ Visual premium com gradientes e neon

⚡ Principais Módulos
🗃️ Gestão de Estoque

Controle completo com atualização visual

Categorias e organização por tipo

Quantidades imediatas sem conferência física

Histórico de movimentações

Filtros inteligentes e interface moderna

🧼 Cronograma de Limpeza

Planejamento quinzenal automático

Histórico de ações realizadas

Filtros por período

Regras inteligentes (evita dia 1–4)

Interface com cards e seções dinâmicas

👥 Gestão de Colaboradores

Escalas

Perfis e credenciais

Atribuições e permissões

🛢️ Banco de Dados + Backups

Backup automático (hora a hora)

Snapshots antes de restauração

Download / excluir / restaurar

Painel administrativo seguro

🌐 Tecnologias

Python 3.10+

Flask + Login Manager

SQLAlchemy

Bootstrap 5.3

Waitress (produção Windows)

FontAwesome

Matplotlib / ReportLab

SQLite / PostgreSQL

📦 Instalação
pip install -r requirements.txt


Crie e ative a venv:

python -m venv .venv
.\.venv\Scripts\activate

▶️ Executando o Sistema

(Recomendado — Windows)

start_local.cmd


Ou simplesmente:

python app.py


Acesse:

👉 http://localhost:5000

⚙️ Configuração com Variáveis

As principais:

HOST
PORT
DEBUG
SQLALCHEMY_DATABASE_URI
SENHA_ADMIN
SENHA_OPERADOR
DB_BACKUP_ENABLED
KEEPALIVE_ENABLED
KEEPALIVE_URL
KEEPALIVE_INTERVAL


Pode usar .env.txt na raiz.

💾 Backups & Snapshots

Backup automático a cada hora

Mantém os 10 mais recentes

Snapshot antes de restaurar

Restaurar backup com um clique

Restaurar snapshot pré-restauração

🔐 Login

Usuários padrão:

admin

operador

Senhas definidas por variáveis ou na primeira execução.