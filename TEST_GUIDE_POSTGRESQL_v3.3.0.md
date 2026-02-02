# 🧪 Guia de Testes - PostgreSQL v3.3.0

## Fase 1: Setup Local

### 1.1 Preparar Ambiente
```bash
cd c:\Users\Ciano\Documents\MultiMax-DEV

# Copiar .env
cp .env.example .env

# Verificar DATABASE_URL está correto:
# DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
```

### 1.2 Docker Compose
```bash
# Iniciar serviços
docker-compose up -d

# Verificar status
docker-compose ps

# Logs
docker-compose logs -f postgres   # Deve estar healthy
docker-compose logs -f multimax   # Deve estar rodando
```

### 1.3 Verificar PostgreSQL
```bash
# Conectar ao banco
docker-compose exec postgres psql -U multimax -d multimax

# Listar tabelas (devem estar vazias ainda)
\dt

# Sair
\q
```

## Fase 2: Migrations

### 2.1 Executar Alembic
```bash
# Entrar no container Flask
docker-compose exec multimax bash

# Configurar variável
export DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax

# Ver status atual
alembic current
# Deve retornar: "This environment does not have a database configured"

# Ver histórico
alembic history
# Deve mostrar: 001_initial_tables

# Fazer upgrade
alembic upgrade head
# Deve criar todas as 12 tabelas

# Verificar que upgradou
alembic current
# Deve retornar: 001_initial_tables

# Sair
exit
```

### 2.2 Verificar Tabelas Criadas
```bash
# Conectar ao postgres
docker-compose exec postgres psql -U multimax -d multimax

# Listar tabelas
\dt

# Deve mostrar:
# - users
# - colaboradores
# - ciclos_semanais
# - ciclos_mensais
# - historico_colaborador
# - escalas
# - whatsapp_config
# - whatsapp_messages
# - log_erros
# - log_whatsapp
# - log_deploy
# - heartbeat

# Ver schema da tabela users
\d users

# Deve mostrar colunas: id, username, email, password_hash, role, ativo, created_at, updated_at
```

## Fase 3: Seed Data

### 3.1 Executar Seed
```bash
# Conectar ao container
docker-compose exec multimax bash

# Executar seed
python scripts/seed_database.py

# Saída esperada:
# 🌱 Iniciando seed do banco de dados...
# 📝 Criando usuário admin...
# 📞 Criando configuração de telefone de alerta...
# 🔐 Criando token webhook...
# ✅ Seed concluído com sucesso!

# Sair
exit
```

### 3.2 Verificar Dados
```bash
# Conectar ao postgres
docker-compose exec postgres psql -U multimax -d multimax

# Ver usuários
SELECT * FROM users;

# Deve mostrar: admin | admin@multimax.local

# Ver config
SELECT * FROM whatsapp_config;

# Deve mostrar:
# - alert_phone | +55 11 98765-4321
# - webhook_token | seu_token_webhook_aqui

# Sair
\q
```

## Fase 4: API Tests

### 4.1 Health Check
```bash
# Verificar se Flask está respondendo
curl -i http://localhost:5000/health

# Esperado: 200 OK
```

### 4.2 GET Alert Phone
```bash
# Ler telefone de alerta
curl -i http://localhost:5000/api/settings/alert-phone

# Esperado:
# HTTP/1.1 200 OK
# {
#   "status": "success",
#   "data": {
#     "phone": "+55 11 98765-4321",
#     "description": "Telefone padrão para alertas do sistema",
#     "active": true,
#     "updated_at": "2024-01-15T..."
#   }
# }
```

### 4.3 PUT Alert Phone
```bash
# Atualizar telefone (simulando requisição autenticada)
curl -X PUT http://localhost:5000/api/settings/alert-phone \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+55 11 99999-8888",
    "description": "Novo gerente"
  }'

# Esperado: 200 OK com dados atualizados

# Verificar que foi salvo
curl http://localhost:5000/api/settings/alert-phone

# Deve retornar o novo número
```

### 4.4 POST Test Alert
```bash
# Enviar teste (simulando requisição autenticada)
curl -X POST http://localhost:5000/api/settings/alert-phone/test \
  -H "Content-Type: application/json"

# Esperado: 200 OK com mensagem de sucesso
# {
#   "status": "success",
#   "message": "Mensagem de teste enviada para +55 11 99999-8888"
# }
```

### 4.5 Error Logging
```bash
# Provocar erro 404
curl -i http://localhost:5000/api/inexistente

# Esperado: 404 com request_id
# {
#   "status": "error",
#   "message": "Not Found",
#   "request_id": "uuid-aqui"
# }

# Verificar que foi logado
docker-compose exec postgres psql -U multimax -d multimax -c \
  "SELECT nivel, descricao, request_id FROM log_erros ORDER BY created_at DESC LIMIT 1;"

# Deve mostrar: WARNING | Not Found | uuid
```

## Fase 5: UI Tests

### 5.1 Abrir Dashboard
```bash
# Ir para http://localhost:5000
# Ou usar curl para obter o card HTML
curl -s http://localhost:5000 | grep -A 50 "Central de Notificações"

# Deve conter: card, botões Carregar, Salvar, Teste, Limpar
```

### 5.2 Teste Manual UI (se possível)
```
1. Abrir browser em http://localhost:5000
2. Navegar até card "Central de Notificações WhatsApp"
3. Clicar em "Carregar" → Deve aparecer "+55 11 99999-8888"
4. Alterar para "+55 11 97777-6666"
5. Clicar em "Salvar" → Deve confirmar sucesso
6. Clicar em "Teste" → Deve confirmar envio
7. Clicar em "Limpar" → Deve limpar campos
```

## Fase 6: Validação Final

### 6.1 Checklist de Verificação
```bash
✅ Docker Compose rodando
  docker-compose ps | grep "Up"

✅ PostgreSQL funcional
  docker-compose exec postgres pg_isready -U multimax

✅ 12 Tabelas criadas
  docker-compose exec postgres psql -U multimax -d multimax -c "\dt"

✅ Dados seedados
  docker-compose exec postgres psql -U multimax -d multimax -c "SELECT COUNT(*) FROM users;"

✅ API respondendo
  curl -i http://localhost:5000/api/settings/alert-phone

✅ Erros sendo logados
  docker-compose exec postgres psql -U multimax -d multimax -c "SELECT COUNT(*) FROM log_erros;"

✅ Migration reversível
  alembic downgrade base  # Deve funcionar
  alembic upgrade head    # Deve refazer

✅ Seed idempotente
  python scripts/seed_database.py  # Deve pular se já existe
```

### 6.2 Teste de Performance
```bash
# Carregar múltiplas vezes
for i in {1..100}; do
  curl -s http://localhost:5000/api/settings/alert-phone > /dev/null
  echo "Request $i"
done

# Verificar que todas foram rápidas
# Deve ter < 100ms por requisição
```

### 6.3 Teste de Rollback
```bash
# Fazer downgrade de migrations
alembic downgrade base

# Verificar que tabelas foram deletadas
docker-compose exec postgres psql -U multimax -d multimax -c "\dt"
# Deve retornar: "Did not find any relations"

# Fazer upgrade novamente
alembic upgrade head

# Verificar que tabelas voltaram
docker-compose exec postgres psql -U multimax -d multimax -c "\dt"
```

## Fase 7: Logs e Monitoring

### 7.1 Ver Logs de Erro
```bash
docker-compose exec postgres psql -U multimax -d multimax << EOF
SELECT 
  id, 
  nivel, 
  descricao, 
  request_id, 
  created_at
FROM log_erros 
ORDER BY created_at DESC 
LIMIT 10;
EOF
```

### 7.2 Ver Heartbeat
```bash
docker-compose exec postgres psql -U multimax -d multimax << EOF
SELECT 
  container, 
  status, 
  versao, 
  created_at
FROM heartbeat 
ORDER BY created_at DESC 
LIMIT 5;
EOF
```

### 7.3 Ver Mensagens WhatsApp
```bash
docker-compose exec postgres psql -U multimax -d multimax << EOF
SELECT 
  telefone_destino, 
  tipo, 
  status, 
  created_at
FROM whatsapp_messages 
ORDER BY created_at DESC 
LIMIT 10;
EOF
```

## Fase 8: Cleanup

### 8.1 Limpar Tudo
```bash
# Se precisar refazer tudo:
docker-compose down -v  # Remove volumes!
docker-compose up -d    # Recrear

# Esperar PostgreSQL
sleep 15

# Fazer migrations novamente
export DATABASE_URL=postgresql://multimax:multimax123@postgres:5432/multimax
alembic upgrade head
python scripts/seed_database.py
```

## 🚨 Troubleshooting

### PostgreSQL não inicia
```bash
docker-compose logs postgres
# Verificar se porta 5432 não está em uso
netstat -an | grep 5432
```

### Migration falha
```bash
# Ver erro completo
alembic upgrade head -v

# Resetar se necessário
alembic downgrade base
rm alembic/versions/*.py  # CUIDADO!
```

### API retorna erro 500
```bash
# Ver logs
docker-compose logs multimax | tail -50

# Verificar se DATABASE_URL está correto
docker-compose exec multimax printenv DATABASE_URL
```

### Seed script falha
```bash
# Ver erro
python scripts/seed_database.py

# Se disser "já existe", limpar database:
docker-compose down -v
```

---

**Status**: ✅ Pronto para Testes  
**Versão**: 3.3.0  
**Data**: Jan 2024
