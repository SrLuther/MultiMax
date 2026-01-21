# 🔍 Análise Minuciosa: Como Aconteceu o Bug de Folgas Fantasmas

## 📊 Resumo Executivo

O bug das folgas fantasmas ocorreu por uma **cascata de erros de sincronização** entre criação e leitura de dados:

1. **v2.7.13**: Migração adicionou colunas `setor_id` (mas dados existentes ficaram NULL)
2. **v2.7.14**: Queries de LEITURA começaram a filtrar por `setor_id`
3. **v2.7.15**: Queries de ESCRITA foram corrigidas para PREENCHER `setor_id`
4. **Resultado**: Folgas criadas ANTES de v2.7.15 não tinham `setor_id` preenchido → Não filtravam corretamente

---

## 🏗️ Estrutura de Dados

### Tabelas Envolvidas

```
┌─────────────────────────────────┐
│ ciclo (Hora)                    │
├─────────────────────────────────┤
│ id           INT PK              │
│ collaborator_id INT FK           │ → Collaborator
│ data_lancamento DATE             │
│ origem VARCHAR (ex: "Folga utilizada")
│ valor_horas DECIMAL (-8 para folga)
│ setor_id INT FK                  │ → Setor ✅ v2.7.13
│ status_ciclo VARCHAR ("ativo"/"fechado")
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ ciclo_folga (Folga Manual)       │
├─────────────────────────────────┤
│ id           INT PK              │
│ collaborator_id INT FK           │ → Collaborator
│ data_folga DATE                  │
│ tipo VARCHAR ("adicional"/"uso") │
│ dias INT                         │
│ setor_id INT FK                  │ → Setor ✅ v2.7.13
│ status_ciclo VARCHAR ("ativo"/"fechado")
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ collaborator (Colaborador)       │
├─────────────────────────────────┤
│ id           INT PK              │
│ setor_id INT FK (setor atual)    │ → Setor
│ ...
└─────────────────────────────────┘
```

---

## 🔴 O Bug: Passo a Passo

### Cenário que Causou o Bug:

**Data: 20/01/2026**

1. **Antes de v2.7.13 (Estado Original)**:
   - Tabelas `ciclo_folga` e `ciclo` NÃO tinham coluna `setor_id`
   - Diogo cria uma folga manual no dia 20/01
   - ❌ Nenhum `setor_id` foi gravado (coluna não existia)

2. **v2.7.13 Executado (Migração)**:
   - Adiciona coluna `setor_id` com `DEFAULT NULL`
   - ⚠️ Registros existentes do dia 20/01 têm `setor_id = NULL`

3. **v2.7.14 Desplegado (Sem Migração Posterior)**:
   - PDF começa a filtrar: `Ciclo.setor_id == colab.setor_id`
   - Lógica de filtro: `NULL != 1` → TRUE (não filtra)
   - ❌ Folga do dia 20 ainda aparece (porque setor_id é NULL)

4. **v2.7.15 Desplegado (Sem Recriação)**:
   - Novas folgas agora recebem `setor_id` corretamente
   - ⚠️ Folgas ANTIGAS ainda têm `setor_id = NULL`
   - ❌ Bug persiste para dados antigos

---

## 🔎 Análise das Queries

### Rota 1: `folgas_adicionar()` - CRIAR folga manual

**ANTES de v2.7.15 (BUGADO)**:
```python
# Linhas ~1330-1340
f = CicloFolga()
f.collaborator_id = cid
f.nome_colaborador = collaborator.name
f.data_folga = data_folga
# ❌ FALTA: f.setor_id = collaborator.setor_id
f.tipo = tipo
f.dias = dias
f.observacao = obs if obs else None
f.status_ciclo = "ativo"
```

**Problema**: Se colaborador muda de setor depois, folgas antigas aparecem em PDF novo

---

### Rota 2: `lancar_horas()` - CRIAR "Folga utilizada"

**ANTES de v2.7.15 (CORRETO)**:
```python
# Linhas ~1240
ciclo.setor_id = collaborator.setor_id  # ✅ JÁ ESTAVA CORRETO
```

**Por que funcionava?** Porque "Lançar Horas" foi implementado DEPOIS que setor foi criado

---

### Rota 3: `ocorrencias_adicionar()` - CRIAR ocorrência

**ANTES de v2.7.15 (BUGADO)**:
```python
# Linhas ~1385-1395
o = CicloOcorrencia()
o.collaborator_id = cid
o.nome_colaborador = collaborator.name
o.data_ocorrencia = data_oc
# ❌ FALTA: o.setor_id = collaborator.setor_id
o.tipo = tipo
o.descricao = desc if desc else None
o.status_ciclo = "ativo"
```

---

## 📖 As Queries de LEITURA (PDFs)

### Query de Folgas - `pdf_geral_ciclo()` Linha 2589-2598

```python
folgas = (
    CicloFolga.query.filter(
        CicloFolga.status_ciclo == "fechado",
        CicloFolga.ciclo_id == ciclo_id,
        CicloFolga.collaborator_id == colab.id,
        CicloFolga.data_folga >= w.week_start,
        CicloFolga.data_folga <= w.week_end,
    )
    .order_by(CicloFolga.data_folga.asc(), CicloFolga.id.asc())
    .all()
)
```

**⚠️ NÃO filtra por `setor_id`!** 
- Se `CicloFolga` tem `setor_id = NULL` (dados antigos), aparece mesmo assim

**Correção necessária:**
```python
CicloFolga.setor_id == colab.setor_id,  # Adicionar este filtro
```

---

### Query de "Folgas Utilizadas" - `pdf_geral_ciclo()` Linha 2602-2614

```python
folgas_utilizadas_ciclo = (
    Ciclo.query.filter(
        Ciclo.status_ciclo == "fechado",
        Ciclo.ciclo_id == ciclo_id,
        Ciclo.collaborator_id == colab.id,
        Ciclo.data_lancamento >= w.week_start,
        Ciclo.data_lancamento <= w.week_end,
        Ciclo.origem == "Folga utilizada",
    )
    .order_by(Ciclo.data_lancamento.asc(), Ciclo.id.asc())
    .all()
)
```

**⚠️ NÃO filtra por `setor_id` em v2.7.13**
- Registros da tabela `Ciclo` com `setor_id = NULL` ainda aparecem

**v2.7.14 Adicionado (Linha 2611)**:
```python
Ciclo.setor_id == colab.setor_id,  # Filtro adicionado
```

**Mas ainda afeta dados com `setor_id = NULL`**

---

## 💡 Por Que "NULL != INT" Ainda Mostra?

Em SQL/SQLAlchemy:
```sql
NULL = 1          → Unknown (não entra no filtro)
NULL != 1         → Unknown (não entra no filtro)
NULL IS NULL      → True
setor_id IS NOT NULL  → False para NULL
```

**Problema**: Quando `setor_id = NULL`:
- `CicloFolga.setor_id == colab.setor_id` → NULL (não filtra)
- Resultado: linha ainda aparece!

---

## ✅ Solução Definitiva (3 Partes)

### Parte 1: Corrigir Escrita (v2.7.15) ✅ FEITO
```python
f.setor_id = collaborator.setor_id  # Linha 1335
o.setor_id = collaborator.setor_id  # Linha 1391
```

### Parte 2: Corrigir Leitura - CicloFolga (FALTA)

No `pdf_geral_ciclo()`, linha ~2589:
```python
folgas = (
    CicloFolga.query.filter(
        CicloFolga.status_ciclo == "fechado",
        CicloFolga.ciclo_id == ciclo_id,
        CicloFolga.collaborator_id == colab.id,
        CicloFolga.setor_id == colab.setor_id,  # ⭐ ADICIONAR
        CicloFolga.data_folga >= w.week_start,
        CicloFolga.data_folga <= w.week_end,
    )
    ...
)
```

### Parte 3: Corrigir Dados Antigos (CRÍTICO)

**Para registros com `setor_id = NULL`**, executar migração:

```python
# Migração SQL
UPDATE ciclo_folga 
SET setor_id = (
    SELECT collaborator.setor_id 
    FROM collaborator 
    WHERE collaborator.id = ciclo_folga.collaborator_id
)
WHERE setor_id IS NULL;

UPDATE ciclo_ocorrencia
SET setor_id = (
    SELECT collaborator.setor_id 
    FROM collaborator 
    WHERE collaborator.id = ciclo_ocorrencia.collaborator_id
)
WHERE setor_id IS NULL;

UPDATE ciclo
SET setor_id = (
    SELECT collaborator.setor_id 
    FROM collaborator 
    WHERE collaborator.id = ciclo.collaborator_id
)
WHERE setor_id IS NULL;
```

---

## 🎯 Checklist Final para Correção Total

- [ ] **v2.7.15 Deployado**: Escrita de `setor_id` corrigida ✅
- [ ] **Adicionar filtro em CicloFolga queries**: Leitura de `ciclo_folga` corrigida
- [ ] **Executar Migração NULL→setor**: Dados antigos limpos
- [ ] **Testar PDF após migração**: Folgas fantasmas desaparecerão
- [ ] **Verificar todas as 4 rotas de PDF**: Aplicar mesmo padrão

---

## 📝 Raízes Profundas do Erro

1. **Design não-atômico**: Migração de schema (v2.7.13) separada de correções (v2.7.14/15)
2. **NULL como valor de dados**: Campos que não deveriam ser NULL
3. **Queries inconsistentes**: Algumas filtravam `setor_id`, outras não
4. **Sem constraint NOT NULL**: Banco permitiu NULLs em campo crítico
5. **Dados antigos não migrados**: Registros pré-v2.7.13 ficaram orphans

---

## 🚀 Próximos Passos Recomendados

1. Criar nova migração para limpar NULLs
2. Adicionar `NOT NULL DEFAULT 1` ao `setor_id` em futuras alterações
3. Implementar tests que validam todas as queries com múltiplos setores
4. Considerar arquitetura multi-tenant para futuro
