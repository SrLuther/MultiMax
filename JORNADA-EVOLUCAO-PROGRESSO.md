# Evolução do Módulo Jornada - Progresso de Implementação

## ✅ Concluído

### 1. Migração de Dados 2025
- ✅ Função `_migrate_2025_to_closed()` criada
- ✅ Migração idempotente usando `AppSetting` para rastreamento
- ✅ Endpoint `/jornada/migrate-2025` (apenas DEV)
- ✅ Altera status de meses 2025 de 'aberto' para 'fechado'
- ✅ Não altera dados (horas, dias, folgas, datas, cálculos)
- ✅ Registra execução para evitar reexecução

## 🚧 Em Progresso

### 2. Arquivamento por Período
- ⏳ Melhorar validação de períodos
- ⏳ Garantir transações atômicas
- ⏳ Validação de status FECHADO_REVISAO antes de arquivar

### 3. Página "Situação Final"
- ⏳ Endpoint `/jornada/situacao-final`
- ⏳ Consolidação de dados ativos por colaborador
- ⏳ Template `situacao_final.html`

### 4. Card Resumo Padronizado
- ⏳ Componente reutilizável
- ⏳ Aplicar em todas as subpáginas

### 5. Ajustes Visuais Dark/Light
- ⏳ Tokens de cor separados
- ⏳ Melhorar contraste (AA)
- ⏳ Ajustar tabelas e cards

### 6. Geração de PDF
- ⏳ Implementar do zero
- ⏳ Visualizar, baixar, imprimir
- ⏳ Para todas as subpáginas

### 7. Validação de Permissões
- ⏳ Revisar todas as rotas críticas
- ⏳ Garantir validação no backend

## 📝 Notas Técnicas

- Migração usa `AppSetting` com chave `jornada_migration_2025_completed`
- Função pode ser chamada múltiplas vezes sem efeitos colaterais
- Status alterado apenas de 'aberto' para 'fechado' (não para 'arquivado')
