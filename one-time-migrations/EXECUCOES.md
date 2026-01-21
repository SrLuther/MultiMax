# Lista de Migrações Executadas

Registre aqui quando cada migração foi executada com sucesso.

## ✅ Migrações Aplicadas

### 2026_01_21_add_setor_id_to_ciclo_folga_ocorrencia.py
- **Dev Local**: ✅ 2026-01-21 (Executado com sucesso)
  - Adicionado setor_id em ciclo_folga ✓
  - Adicionado setor_id em ciclo_ocorrencia ✓
  - Registros existentes atualizados com setor do colaborador ✓
  - 0 registros atualizados (tabelas vazias)
- **VPS Produção**: ⏳ Pendente
- **Status**: Sincronização de schema do banco com modelos
- **Motivo**: Erro "no such column: ciclo_folga.setor_id" estava impedindo consultas
- **Pode deletar?**: ❌ Não (aguardar produção)

### 2026_01_21_add_setor_to_collaborator.py
- **Dev Local**: ✅ 2026-01-20 (Executado com sucesso)
  - Adicionado setor_id em collaborator ✓
  - Adicionado setor_id em ciclo ✓ (ATUALIZADO)
  - Índices criados ✓
- **VPS Produção**: ⏳ Pendente
- **Status**: Aguardando deploy em produção
- **Pode deletar?**: ❌ Não (aguardar produção)

### 2026_01_20_create_setores.py
- **Dev Local**: ✅ 2026-01-20 (Executado com sucesso)
  - 4 setores criados: Açougue, Estoque, Produção, Expedição ✓
  - 6 colaboradores atribuídos ao Açougue ✓
  - 30 lançamentos de teste criados (15h cada colaborador) ✓
- **VPS Produção**: ⏳ Pendente
- **Status**: Populando dados base do sistema
- **Pode deletar?**: ❌ Não (aguardar produção + testes)

---

## 📋 Template para Novos Registros

```markdown
### YYYY_MM_DD_nome_da_migracao.py
- **Dev Local**: ⏳ Pendente | ✅ Data
- **VPS Produção**: ⏳ Pendente | ✅ Data
- **Status**: Descrição do status atual
- **Pode deletar?**: ❌ Não | ✅ Sim (após 7 dias estável)
```
