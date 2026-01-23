# MultiMax - Configuração de Banco de Dados

## Visão Geral

MultiMax suporta dois tipos de banco de dados:
- **PostgreSQL** (recomendado para produção)
- **SQLite** (para desenvolvimento/pequenos servidores)

---

## PostgreSQL (Produção)

### Instalação

```bash
# Instalado automaticamente pelo setup.sh, mas se precisar manual:
sudo apt-get install postgresql postgresql-contrib

# Iniciar serviço
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Criação de Usuário e Banco

```bash
# Acessar console PostgreSQL
sudo -u postgres psql

# Dentro do psql:
CREATE USER multimax WITH PASSWORD 'SUA_SENHA_FORTE_AQUI';
CREATE DATABASE multimax_db OWNER multimax;

# Configurar encoding
ALTER DATABASE multimax_db SET ENCODING 'UTF8';
ALTER DATABASE multimax_db SET DATESTYLE = 'ISO, DMY';

# Sair
\q
```

### Configuração em `.env`

```env
# Formato completo (com credenciais)
DATABASE_URL=postgresql+psycopg://multimax:SUA_SENHA@localhost:5432/multimax_db

# Com SSL (recomendado)
DATABASE_URL=postgresql+psycopg://multimax:SUA_SENHA@localhost:5432/multimax_db?sslmode=require
```

### Backup (pg_dump)

```bash
# Full backup
sudo -u multimax pg_dump DATABASE_URL > backup.sql

# Compressed
sudo -u multimax pg_dump DATABASE_URL | gzip > backup.sql.gz

# Com date
sudo -u multimax pg_dump DATABASE_URL | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Usar script de deploy
cd /opt/multimax/deploy/scripts
sudo -u multimax ./db-manager.sh backup
```

### Restore

```bash
# Do arquivo
sudo -u multimax psql DATABASE_URL < backup.sql

# Compressed
sudo -u multimax gunzip -c backup.sql.gz | psql DATABASE_URL

# Usar script
sudo -u multimax ./db-manager.sh restore /path/to/backup.sql.gz
```

### Manutenção

```bash
# Vacuum (limpeza)
sudo -u postgres vacuumdb multimax_db

# Analyze (statisticas)
sudo -u postgres analyzedb multimax_db

# Reindex (recriar índices)
sudo -u postgres reindexdb multimax_db

# Full maintenance
sudo -u postgres vacuumdb -f -z multimax_db
```

### Monitoramento

```bash
# Tamanho do banco
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('multimax_db'));"

# Conexões ativas
sudo -u postgres psql -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Queries lentas (log)
sudo tail -f /var/log/postgresql/postgresql-14-main.log | grep "duration:"

# Verificar índices
sudo -u postgres psql multimax_db -c "SELECT * FROM pg_indexes WHERE schemaname != 'pg_catalog';"
```

### Tuning (Performance)

Editar `/etc/postgresql/14/main/postgresql.conf`:

```ini
# Para servidor com 4GB RAM
max_connections = 200
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 5MB
maintenance_work_mem = 256MB
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging de queries lentas
log_statement = 'all'
log_min_duration_statement = 1000  # Ms
```

Depois restart:
```bash
sudo systemctl restart postgresql
```

---

## SQLite (Desenvolvimento)

### Configuração

```env
# Em .env ou command line
DATABASE_URL=sqlite:////var/lib/multimax/estoque.db
DB_FILE_PATH=/var/lib/multimax/estoque.db
```

### Vantagens
- ✅ Zero configuração
- ✅ Sem server externo
- ✅ Arquivo único
- ✅ Bom para até ~10GB

### Desvantagens
- ❌ Não escalável (sem concorrência pesada)
- ❌ Backup manual necessário
- ❌ Sem replicação

### Backup

```bash
# Simples cópia
cp /var/lib/multimax/estoque.db /var/lib/multimax/backups/estoque_$(date +%Y%m%d_%H%M%S).db

# Com dump SQL
sqlite3 /var/lib/multimax/estoque.db ".dump" | gzip > backup.sql.gz

# Usar script
sudo -u multimax ./db-manager.sh backup
```

---

## Migração PostgreSQL → SQLite ou vice-versa

### PostgreSQL → SQLite

```bash
# 1. Dump PostgreSQL
pg_dump DATABASE_URL > dump.sql

# 2. Converter schema
# (pode exigir ajustes manuais)

# 3. Importar em SQLite
sqlite3 /var/lib/multimax/estoque.db < dump.sql
```

### SQLite → PostgreSQL

```bash
# 1. Dump SQLite
sqlite3 /var/lib/multimax/estoque.db ".dump" > dump.sql

# 2. Importar PostgreSQL
psql DATABASE_URL < dump.sql

# Ou usar ferramenta como pgloader
```

---

## Alembic Migrations

### Estrutura

```
/opt/multimax/
└── migrations/
    ├── alembic.ini          # Config Alembic
    ├── env.py               # Environment script
    └── versions/
        ├── 001_initial.py
        ├── 002_add_users.py
        └── ...
```

### Criar Migration

```bash
cd /opt/multimax
source venv/bin/activate

# Auto-detect de mudanças
alembic revision --autogenerate -m "Descrição da mudança"

# Manual
alembic revision -m "Descrição"
```

### Aplicar Migrations

```bash
# Atualizar para versão mais recente
alembic upgrade head

# Upgrade para versão específica
alembic upgrade +2  # 2 versões pra frente
alembic upgrade 12abc  # commit específico

# Downgrade
alembic downgrade -1  # 1 versão para trás
alembic downgrade base  # reverter tudo
```

### Ver histórico

```bash
# Versão atual
alembic current

# Histórico
alembic history

# Branches
alembic branches
```

---

## Pooling de Conexão

### SQLAlchemy Connection Pool

No `.env`:
```env
# Pool configuration
SQLALCHEMY_ENGINE_OPTIONS={"pool_size": 10, "max_overflow": 20, "pool_recycle": 3600}
```

- **pool_size=10**: Manter 10 conexões abertas
- **max_overflow=20**: Permitir 20 extras quando necessário
- **pool_recycle=3600**: Reciclar conexões a cada 1 hora

### Monitoramento

```bash
# Ver pool status
sudo -u multimax python3 -c "
from multimax import create_app
app = create_app()
db = app.db
print(f'Pool: {db.engine.pool}')
print(f'Tamanho: {db.engine.pool.size()}')
"
```

---

## Replicação e HA (High Availability)

### PostgreSQL Streaming Replication

Para múltiplos servidores:

1. **Primary** (servidor principal)
2. **Standby** (servidor secundário, réplica)

Consulte documentação PostgreSQL oficial para setup detalhado.

---

## Backup Automatizado (Cron)

### Configurar backup diário

```bash
# Adicionar ao crontab do multimax
sudo -u multimax crontab -e

# Backup às 2 AM diariamente
0 2 * * * /opt/multimax/deploy/scripts/db-manager.sh backup

# Cleanup de backups com mais de 30 dias (já feito pelo script)
# (Implementado em db-manager.sh)
```

### Backup remoto

```bash
# Adicionar ao crontab
0 2 * * * /opt/multimax/deploy/scripts/db-manager.sh backup && \
           s3cmd put /var/lib/multimax/backups/*.sql.gz s3://seu-bucket/multimax/

# Ou usar rclone
rclone copy /var/lib/multimax/backups/ remote:multimax/backups/ --delete-after
```

---

## Troubleshooting

### Erro: "Connection refused"

```bash
# 1. Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# 2. Checar porta
sudo netstat -tlnp | grep 5432

# 3. Testar conexão
sudo -u postgres psql -d multimax_db

# 4. Ver arquivo .env
cat /opt/multimax/.env | grep DATABASE_URL
```

### Erro: "Database does not exist"

```bash
# 1. Listar bancos existentes
sudo -u postgres psql -l

# 2. Criar banco
sudo -u postgres createdb multimax_db -O multimax

# 3. Rerun migrations
cd /opt/multimax && alembic upgrade head
```

### Erro: "Permission denied"

```bash
# Verificar proprietário
ls -la /var/lib/multimax/

# Corrigir
sudo chown multimax:multimax /var/lib/multimax/estoque.db
sudo chmod 600 /var/lib/multimax/estoque.db  # Se SQLite
```

### Banco muito grande

```bash
# 1. Ver tamanho
du -sh /var/lib/multimax/

# 2. Limpar dados antigos (application-specific)
# ... (depende da lógica do app)

# 3. Vacuum (PostgreSQL)
sudo -u postgres vacuumdb -f multimax_db

# 4. Backup e restore (SQLite)
sqlite3 /var/lib/multimax/estoque.db "VACUUM INTO '/tmp/clean.db';" && \
mv /tmp/clean.db /var/lib/multimax/estoque.db
```

---

## Segurança

### Senhas Fortes

```bash
# Gerar senha aleatória
openssl rand -base64 16

# Usar em DATABASE_URL
DATABASE_URL=postgresql://multimax:SENHA_AQUI@localhost/multimax_db
```

### Permissões PostgreSQL

```sql
-- Usuário apenas leitura
CREATE USER readonly WITH PASSWORD 'senha';
GRANT CONNECT ON DATABASE multimax_db TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
```

### Backup Criptografado

```bash
# Com GPG
sudo -u multimax pg_dump DATABASE_URL | gzip | gpg -c > backup.sql.gz.gpg

# Restaurar
gpg -d backup.sql.gz.gpg | gunzip | psql DATABASE_URL
```

---

**Última atualização:** 23 de janeiro de 2026  
**PostgreSQL 14+** | **SQLite 3.40+** | **Ubuntu 24.04 LTS**
