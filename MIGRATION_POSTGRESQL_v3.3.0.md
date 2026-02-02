# Migração PostgreSQL - MultiMax v3.3.0

## 📋 Resumo

Este documento descreve a migração completa do MultiMax de SQLite para PostgreSQL, com Flask como ponto central de controle e Node.js como executor HTTP puro.

## 🏗️ Arquitetura Nova

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL 15                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Tables:                                         │   │
│  │ - users, colaboradores, ciclos, escalas        │   │
│  │ - whatsapp_config, whatsapp_messages            │   │
│  │ - log_erros, log_whatsapp, log_deploy           │   │
│  │ - heartbeat                                     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
           ↑                              ↑
           │ read/write                   │ read only
           │                              │
    ┌──────▼──────────────────────────────▼──────┐
    │         Flask API (Python)                   │
    │ ┌─────────────────────────────────────────┐ │
    │ │ Routes:                                 │ │
    │ │ - /api/settings/alert-phone (GET/PUT)  │ │
    │ │ - /api/errors (logging)                 │ │
    │ │ - /api/whatsapp/* (messaging)           │ │
    │ │ - /api/schedules/* (escalas)            │ │
    │ │ - Middleware global de erros            │ │
    │ └─────────────────────────────────────────┘ │
    └──────────────────────────────────────────────┘
           ↑              ↑
           │ HTTP         │ HTTP
           │ GET/PUT      │ POST
           │              │
    ┌──────▼────┐   ┌─────▼─────────┐
    │    UI      │   │ WhatsApp      │
    │  (React)   │   │ Service (Node)│
    │            │   │               │
    │ Dashboard  │   │ - Executor    │
    │ Forms      │   │ - No DB       │
    │ Alerts     │   │ - Stateless   │
    └────────────┘   └───────────────┘
```

## 📊 Tabelas PostgreSQL

### users
```sql
id, username, email, password_hash, role, ativo, created_at, updated_at
```

### colaboradores
```sql
id, nome, cpf, email, telefone, departamento, funcao,
data_admissao, data_demissao, ativo, horas_ciclo, saldo_horas,
created_at, updated_at
```

### ciclos_semanais
```sql
id, numero_ciclo, data_inicio, data_fim, ativo, observacoes,
created_at, updated_at
```

### ciclos_mensais
```sql
id, mes, ano, data_inicio, data_fim, fechado, created_at, updated_at
```

### historico_colaborador
```sql
id, colaborador_id, ciclo_semanal_id,
horas_trabalhadas, horas_falta, horas_atraso, horas_extra,
observacoes, created_at, updated_at
```

### escalas
```sql
id, colaborador_id, ciclo_semanal_id,
data_escala, tipo_dia, hora_entrada, hora_saida,
intervalo_minutos, turno, setor, observacoes,
created_at, updated_at
```

### whatsapp_config
```sql
id, chave, valor, descricao, ativo, created_at, updated_at
```

### whatsapp_messages
```sql
id, telefone_destino, mensagem, tipo, status,
resposta_whatsapp, erro, ciclo_semanal_id, colaborador_id,
created_at, updated_at, enviado_em
```

### log_erros
```sql
id, nivel, descricao, stack_trace, rota, usuario, container,
request_id, created_at, updated_at
```

### log_whatsapp
```sql
id, acao, telefone, status, detalhes, resposta_api,
created_at, updated_at
```

### log_deploy
```sql
id, versao, evento, status, detalhes, container, created_at
```

### heartbeat
```sql
id, container, status, versao, uptime_segundos,
cpu_percent, memoria_mb, detalhes, created_at
```

## 🚀 Deploy no VPS

### 1. Preparação

```bash
# SSH no VPS
ssh multimax@multimax.local

# Navegar para projeto
cd /opt/multimax

# Backup de segurança (SQLite antigo)
mkdir -p /opt/multimax-backups
cp /multimax-data/estoque.db /opt/multimax-backups/estoque.db.backup.$(date +%s)
```

### 2. Criar .env

```bash
cat > /opt/multimax/.env << EOF
DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
FLASK_ENV=production
FLASK_DEBUG=false
CONTAINER_NAME=flask
WHATSAPP_SERVICE_URL=http://whatsapp-service:3000
EOF
```

### 3. Deploy com Docker Compose

```bash
# Parar containers antigos
docker-compose down

# Atualizar código
git pull origin main

# Construir imagens
docker-compose build

# Iniciar containers
docker-compose up -d

# Verificar logs
docker-compose logs -f multimax
```

### 4. Executar Migrations

```bash
# Conectar ao container Flask
docker-compose exec multimax bash

# Executar Alembic
export DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
alembic upgrade head

# Seed do banco
python scripts/seed_database.py

# Sair do container
exit
```

### 5. Verificar Health

```bash
# Verificar se PostgreSQL está online
docker-compose exec postgres pg_isready -U multimax -d multimax

# Verificar se Flask está respondendo
curl http://localhost:5000/health

# Verificar se WhatsApp Service está online
curl http://localhost:3000/health

# Ver logs de erro
docker-compose logs multimax | grep ERROR
```

## 🔧 APIs Principais

### Alert Phone (Novo)

**GET** `/api/settings/alert-phone`
```json
Response: {
  "status": "success",
  "data": {
    "phone": "+55 11 98765-4321",
    "description": "Gerente de turno",
    "active": true,
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

**PUT** `/api/settings/alert-phone`
```json
Body: {
  "phone": "+55 11 99999-8888",
  "description": "Novo gerente"
}

Response: {
  "status": "success",
  "message": "Telefone de alerta atualizado com sucesso",
  "data": {
    "phone": "+55 11 99999-8888",
    ...
  }
}
```

**POST** `/api/settings/alert-phone/test`
```json
Response: {
  "status": "success",
  "message": "Mensagem de teste enviada para +55 11 99999-8888"
}
```

## 📝 Logging Centralizado

Todos os erros são automaticamente:
1. ✅ Salvos na tabela `log_erros`
2. ✅ Associados a `request_id` único
3. ✅ Incluem stack trace completo
4. ✅ Notificam via WhatsApp se crítico
5. ✅ Retornam `request_id` ao cliente

```python
# Exemplo: Erro capturado automaticamente
GET /api/schedule/invalid-id
→ LogErro criado com request_id
→ Resposta JSON com request_id
→ WhatsApp alerta se CRITICAL
```

## 🧪 Testes Locais

```bash
# Instalar dependências
pip install -r requirements.txt

# Criar .env local
cp .env.example .env

# Docker Compose local
docker-compose up -d

# Esperar PostgreSQL iniciar (10-15s)
sleep 15

# Rodarmigrations
export DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
alembic upgrade head

# Seed
python scripts/seed_database.py

# Rodar testes
python -m pytest tests/ -v

# Verificar APIs
curl http://localhost:5000/api/settings/alert-phone
```

## ✅ Checklist de Migração

- [ ] Backup do SQLite feito
- [ ] .env criado com DATABASE_URL
- [ ] docker-compose up -d
- [ ] PostgreSQL inicializado
- [ ] Alembic upgrade head
- [ ] Seed executado
- [ ] GET /api/settings/alert-phone retorna 200
- [ ] PUT /api/settings/alert-phone funciona
- [ ] POST /api/settings/alert-phone/test funciona
- [ ] Erros aparecem em log_erros
- [ ] WhatsApp recebe alertas críticos
- [ ] Todos os testes passam

## 🚨 Troubleshooting

### PostgreSQL não inicia
```bash
docker-compose logs postgres
# Verificar volume permissions
sudo ls -la /opt/multimax-backups/postgres_data
```

### Erro: "FATAL: role 'multimax' does not exist"
```bash
docker-compose down -v  # Remove volumes!
docker-compose up -d postgres
docker-compose exec postgres psql -U postgres -c "CREATE USER multimax WITH PASSWORD 'multimax123';"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE multimax OWNER multimax;"
```

### Alembic fails
```bash
export DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
alembic history
alembic current
alembic downgrade base  # Rollback se needed
alembic upgrade head    # Retry
```

### Node.js error "db.query() is deprecated"
```
✅ Esperado! Node.js não deve chamar db.js
✅ Use Flask API em /api/settings/alert-phone
✅ Ver whatsapp-service/src/api.js para chamadas HTTP
```

## 📞 Suporte

Qualquer dúvida sobre a migração:
1. Verificar logs: `docker-compose logs multimax`
2. Consultar `log_erros` table: `SELECT * FROM log_erros ORDER BY created_at DESC LIMIT 10;`
3. Testar endpoint: `curl -i http://localhost:5000/api/settings/alert-phone`

---

**Versão**: 3.3.0  
**Data**: Jan 2024  
**Status**: ✅ Completo
