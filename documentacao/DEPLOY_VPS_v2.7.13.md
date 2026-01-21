# 🚀 Instruções de Deploy VPS - v2.7.13 (Docker)

## ⚠️ ATENÇÃO: Migração de Banco de Dados Necessária

Esta versão requer execução de migração de banco de dados na VPS.

**Ambiente:** Docker / Docker Compose

---

## 📋 Passos para Deploy na VPS com Docker

### 1. Fazer Pull das Alterações

```bash
cd /caminho/do/MultiMax-DEV
git pull origin nova-versao-deploy
```

### 2. **IMPORTANTE:** Executar Migração do Banco DENTRO DO CONTAINER

```bash
# Opção 1: Executar migração no container em execução
docker-compose exec multimax python3 one-time-migrations/2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py

# OU Opção 2: Se o container não estiver rodando, executar temporariamente
docker-compose run --rm multimax python3 one-time-migrations/2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py
```

**O que a migração faz:**
- Adiciona coluna `setor_id` na tabela `ciclo_folga`
- Adiciona coluna `setor_id` na tabela `ciclo_ocorrencia`
- Atualiza registros existentes com setor do colaborador
- Se um colaborador não tiver setor, usa setor padrão (ID 1)

### 3. Verificar Resultado da Migração

Você deve ver uma saída como:

```
======================================================================
Migração: Adicionar setor_id em ciclo_folga e ciclo_ocorrencia
======================================================================
Adicionando coluna setor_id em ciclo_folga...
Atualizando setor_id para registros existentes em ciclo_folga...
✓ X registros atualizados em ciclo_folga

Adicionando coluna setor_id em ciclo_ocorrencia...
Atualizando setor_id para registros existentes em ciclo_ocorrencia...
✓ X registros atualizados em ciclo_ocorrencia

✅ Migração concluída com sucesso!
```

### 4. Reconstruir e Reiniciar Containers Docker

```bash
# Reconstruir a imagem com o código atualizado
docker-compose build

### 5. Verificar Logs do Docker

```bash
# Ver logs do container multimax
docker-compose logs -f multimax

# Ou verificar logs das últimas 100 linhas
docker-compose logs --tail=100 multimax

# Verificar se há erros relacionados a setor_id
docker-compose logs multimax | grep -i "setor_id"
```

### 6. Verificar se a Aplicação está Funcionando

```bash
# Verificar status dos containers
docker-compose ps

# Testar conexão HTTP
curl http://localhost:5000/  # ou a porta configurada
```

---

## 🐛 Problema Resolvido

**Antes:** 
- Erro "no such column: ciclo_folga.setor_id" impedia consultas
- Folgas apareciam duplicadas no PDF mesmo após exclusão
- PDF mostrava folgas "fantasmas"

**Depois:**
- Schema do banco sincronizado com modelos
- Consultas funcionando corretamente
- PDF reflete dados reais do banco
- Validações de folgas duplicadas ativas

---

## 📌 Outras Alterações Nesta Versão

### v2.7.12
- Validação para impedir folgas duplicadas no mesmo dia
- Mensagens claras quando tentar criar folga conflitante

### v2.7.11
- Refatoração da função login (redução de complexidade)

### v2.7.10
- Correção de duplicação de folgas em PDFs

### v2.7.9
- Melhoria no formato do cabeçalho do PDF (Janeiro 2026)

---

## ✅ Checklist Pós-Deploy

- [ ] Migração executada com sucesso
- [ ] Aplicação reiniciada
- [ ] Logs verificados (sem erros)
- [ ] PDF testado (não mostra mais folgas fantasmas)
- [ ] Histórico de ciclos funcionando corretamente
- [ ] Criar folga manual testado (com validação de duplicatas)

---

## 🆘 Se Algo Der Errado (Docker)

### Erro: "no such column: setor_id"

**Solução:** Execute a migração novamente dentro do container:
```bash
docker-compose exec multimax python3 one-time-migrations/2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py
```

### Erro: "column setor_id already exists"

**Causa:** Migração já foi executada anteriormente.  
**Ação:** Nenhuma, está tudo certo!

### Container não inicia após rebuild

**Possíveis causas:**
1. Erro na build da imagem - verificar logs: `docker-compose logs multimax`
2. Porta em uso - verificar: `docker-compose ps` e `netstat -tulpn | grep 5000`
3. Volumes com permissões erradas

**Solução:**
```bash
# Verificar logs detalhados
docker-compose logs --tail=200 multimax

# Forçar rebuild completo
docker-compose build --no-cache
docker-compose up -d
```

### PDF ainda mostra folgas fantasmas

**Possíveis causas:**
1. Cache do navegador - testar em modo anônimo (Ctrl+Shift+N)
2. Migração não foi executada no container correto
3. Container não foi reiniciado após migração

**Diagnóstico dentro do container:**
```bash
# Entrar no container
docker-compose exec multimax bash

# Conectar no banco e verificar estrutura
# Para SQLite:
sqlite3 instance/multimax.db ".schema ciclo_folga"

# Para PostgreSQL:
psql -U usuario -d multimax_db -c "\d ciclo_folga"

# Verificar se coluna setor_id existe
sqlite3 instance/multimax.db "PRAGMA table_info(ciclo_folga);"
```

### Verificar estado do banco de dados

```bash
# Entrar no container e verificar folgas do dia 20/01
docker-compose exec multimax python3 -c "
from multimax import create_app, db
from multimax.models import CicloFolga, Ciclo
from datetime import date
app = create_app()
with app.app_context():
    folgas = CicloFolga.query.filter(CicloFolga.data_folga == date(2026, 1, 20)).all()
    print(f'Folgas no dia 20/01: {len(folgas)}')
    horas = Ciclo.query.filter(Ciclo.data_lancamento == date(2026, 1, 20), Ciclo.origem == 'Folga utilizada').all()
    print(f'Horas com folga utilizada: {len(horas)}')
"
```

---

## 📞 Suporte

Se encontrar problemas, verifique:
1. Logs da aplicação
2. Resultado da migração
3. Estrutura do banco de dados (setor_id deve existir)

**Data desta versão:** 21/01/2026
