# Diagnóstico 502 Bad Gateway - MultiMax

## Status do Código Local
✅ **TODOS OS TESTES PASSARAM**
- Flask importa corretamente
- Modelos têm payment_date e payment_amount
- Rotas importam sem erros
- App Flask cria com sucesso
- 24 rotas de jornada registradas

## Problema Identificado
O erro 502 Bad Gateway está ocorrendo na **VPS**, não no código local. O container Docker precisa ser atualizado.

## Solução - Atualizar Container na VPS

### Passo 1: Conectar na VPS
```bash
ssh usuario@multimax.tec.br
```

### Passo 2: Navegar para o diretório do projeto
```bash
cd /caminho/do/projeto/MultiMax
```

### Passo 3: Atualizar código do Git
```bash
git fetch origin
git checkout nova-versao-deploy
git pull origin nova-versao-deploy
```

### Passo 4: Verificar versão atual
```bash
git log --oneline -3
# Deve mostrar:
# 7eb6b83 chore: atualiza versão para 2.3.32 após limpeza de código
# 3371ddd chore: remove arquivos vazios e inutilizados
# b88d969 fix(jornada): corrige NameError de payment_date/payment_amount
```

### Passo 5: Testar código localmente (na VPS)
```bash
python3 test_app.py
# Deve mostrar: [SUCCESS] TODOS OS TESTES PASSARAM
```

### Passo 6: Reconstruir e reiniciar container Docker
```bash
# Parar containers
docker-compose down

# Reconstruir imagem (forçar rebuild)
docker-compose build --no-cache

# Iniciar containers
docker-compose up -d

# Verificar logs
docker-compose logs -f --tail=50
```

### Passo 7: Verificar se container está rodando
```bash
docker-compose ps
# Deve mostrar status "Up" para o container multimax

# Verificar logs de erro
docker-compose logs multimax | tail -100
```

## Verificações Adicionais

### Se o erro persistir após atualização:

1. **Verificar logs do container:**
```bash
docker-compose logs multimax | grep -i error
docker-compose logs multimax | grep -i traceback
```

2. **Verificar se o banco de dados tem as colunas:**
```bash
# Se usar SQLite
sqlite3 /multimax-data/estoque.db "PRAGMA table_info(month_status);"
sqlite3 /multimax-data/estoque.db "PRAGMA table_info(jornada_archive);"

# Se usar PostgreSQL
psql $DATABASE_URL -c "\d month_status"
psql $DATABASE_URL -c "\d jornada_archive"
```

3. **Executar migração manual se necessário:**
```bash
# Entrar no container
docker-compose exec multimax bash

# Executar Python interativo
python3
>>> from multimax import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
...     print("Tabelas criadas/atualizadas")
```

## Correções Aplicadas (v2.3.31 e v2.3.32)

1. **v2.3.31**: Corrigido NameError de `payment_date`/`payment_amount` na função `arquivar`
2. **v2.3.32**: Removidos 8 arquivos vazios/inutilizados

## Arquivos Modificados
- `multimax/routes/jornada.py` - Correção de NameError
- `multimax/models.py` - Já tinha payment_date e payment_amount (OK)
- Removidos arquivos vazios: app_setup.py, health_monitor.py, logging_config.py, rbac_init.py, rbac.py, audit_helper.py, test_rbac.py, cronograma.html.backup

## Contato
Se o problema persistir após seguir todos os passos, verificar:
- Logs do Nginx: `/var/log/nginx/error.log`
- Logs do Docker: `docker-compose logs`
- Status do container: `docker-compose ps`
