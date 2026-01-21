# 🚀 Instruções de Deploy VPS - v2.7.13

## ⚠️ ATENÇÃO: Migração de Banco de Dados Necessária

Esta versão requer execução de migração de banco de dados na VPS.

---

## 📋 Passos para Deploy na VPS

### 1. Fazer Pull das Alterações

```bash
cd /caminho/do/MultiMax-DEV
git pull origin nova-versao-deploy
```

### 2. **IMPORTANTE:** Executar Migração do Banco

```bash
# Ativar ambiente virtual
source venv/bin/activate  # ou o caminho do seu venv

# Executar migração
python one-time-migrations/2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py
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

### 4. Reiniciar Aplicação

```bash
# Dependendo do seu setup:
sudo systemctl restart multimax
# ou
sudo supervisorctl restart multimax
# ou
pm2 restart multimax
```

### 5. Verificar Logs

```bash
# Verificar se não há erros relacionados a setor_id
tail -f /var/log/multimax/error.log
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

## 🆘 Se Algo Der Errado

### Erro: "no such column: setor_id"

**Solução:** Execute a migração novamente:
```bash
python one-time-migrations/2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py
```

### Erro: "column setor_id already exists"

**Causa:** Migração já foi executada anteriormente.  
**Ação:** Nenhuma, está tudo certo!

### PDF ainda mostra folgas fantasmas

**Possíveis causas:**
1. Cache do navegador - testar em modo anônimo
2. Migração não foi executada - verificar logs da migração
3. Aplicação não foi reiniciada - reiniciar serviço

**Diagnóstico:**
```bash
# Conectar no banco e verificar
sqlite3 instance/multimax.db
# ou
psql -d multimax_db

# Verificar estrutura da tabela
.schema ciclo_folga  # SQLite
\d ciclo_folga       # PostgreSQL
```

---

## 📞 Suporte

Se encontrar problemas, verifique:
1. Logs da aplicação
2. Resultado da migração
3. Estrutura do banco de dados (setor_id deve existir)

**Data desta versão:** 21/01/2026
