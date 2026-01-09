# Sistema de Controle de Jornada Mensal - Especificação Técnica

## 📋 Visão Geral

Sistema de controle de jornada mensal inspirado em faturas de cartão de crédito, com controle rígido de estados, permissões e integração com calendário e feriados.

## 🔐 Perfis de Acesso

### DEV
- **Acesso**: Total e irrestrito
- **Pode**: Criar, editar, excluir e corrigir dados em qualquer estado
- **Pode**: Editar meses arquivados
- **Pode**: Reabrir meses se necessário
- **Função**: Responsável técnico e corretor histórico

### ADMIN
- **Acesso**: Gestão operacional
- **Pode editar**: Apenas enquanto o mês NÃO estiver arquivado
- **Após arquivamento**: Perde completamente o direito de edição
- **Mantém**: Visualização e exportação sempre disponíveis

### OPERADOR
- **Acesso**: Exclusivamente consultivo
- **Pode**: Visualizar informações e exportar relatórios
- **NÃO pode**: Editar absolutamente nada
- **Interface**: Campos de edição não devem ser exibidos

## 📅 Estados do Mês

### 🟢 EM ABERTO
- **Descrição**: Mês atual ou disponível para lançamento
- **Permissões**:
  - DEV: Edição total
  - ADMIN: Edição permitida
  - OPERADOR: Apenas visualização/exportação
- **Transição**: Pode ser fechado para revisão

### 🟡 FECHADO PARA REVISÃO
- **Descrição**: Mês encerrado operacionalmente, aguardando confirmação de pagamento
- **Permissões**:
  - DEV: Pode editar
  - ADMIN: Pode editar (ajustes necessários)
  - OPERADOR: Apenas visualização
- **Transição**: Pode ser arquivado após confirmação de pagamento

### 🔴 ARQUIVADO
- **Descrição**: Mês consolidado definitivamente após pagamento confirmado
- **Permissões**:
  - DEV: Pode editar
  - ADMIN: Somente leitura
  - OPERADOR: Somente leitura e exportação
- **Transição**: Não pode ser alterado (exceto por DEV)

## 🔄 Transições de Estado

### Fechar Mês (EM ABERTO → FECHADO)
- **Quem pode**: ADMIN, DEV
- **Ação**: Marca mês como "fechado"
- **Resultado**: Mês fica aguardando confirmação de pagamento

### Confirmar Pagamento (FECHADO → ARQUIVADO)
- **Quem pode**: ADMIN, DEV
- **Ação**: Confirma pagamento e arquiva o mês
- **Resultado**: Mês fica arquivado e protegido contra edições (exceto DEV)

### Reabrir Mês (ARQUIVADO → FECHADO ou EM ABERTO)
- **Quem pode**: Apenas DEV
- **Ação**: Reverte estado do mês
- **Resultado**: Mês volta para estado anterior

## 📄 Subpáginas

### 1. EM ABERTO (`/jornada/em-aberto`)
- **Conteúdo**: Apenas meses com status "aberto"
- **Funcionalidades**: 
  - Listar registros dos meses em aberto
  - Permitir edição (conforme permissões)
  - Calendário automático
  - Integração com feriados

### 2. FECHADO PARA REVISÃO (`/jornada/fechado-revisao`)
- **Conteúdo**: Apenas meses com status "fechado"
- **Funcionalidades**:
  - Listar registros dos meses fechados
  - Permitir edição (DEV e ADMIN)
  - Indicar claramente estado de aguardando pagamento
  - Opção para confirmar pagamento e arquivar

### 3. ARQUIVADOS (`/jornada/arquivados`)
- **Conteúdo**: Apenas meses com status "arquivado"
- **Funcionalidades**:
  - Listar registros arquivados (da tabela JornadaArchive)
  - Apenas visualização (exceto DEV)
  - Histórico completo e consultável
  - Exportação disponível

## 📅 Calendário Automático

### Características
- **Geração**: Automática baseada nos dados da Jornada
- **Atualização**: Tempo real após inserção/edição/exclusão
- **Preenchimento**: Dias preenchidos conforme dados inseridos
- **Fonte de dados**: TimeOffRecord

### Integração com Feriados
- **Fonte única**: Lista de feriados na página Escala (modelo Holiday)
- **Consulta**: Calendário consulta automaticamente os feriados
- **Exibição**: Feriados aparecem automaticamente no calendário
- **Sincronização**: Alterações na Escala refletem automaticamente

## 🗄️ Estrutura de Dados

### MonthStatus (Novo Modelo)
```python
- id: Integer (PK)
- year: Integer (índice)
- month: Integer (1-12, índice)
- status: String ('aberto', 'fechado', 'arquivado')
- closed_at: DateTime (quando foi fechado)
- closed_by: String (quem fechou)
- archived_at: DateTime (quando foi arquivado)
- archived_by: String (quem arquivou)
- payment_confirmed: Boolean
- payment_confirmed_at: DateTime
- payment_confirmed_by: String
- notes: Text
- UniqueConstraint: (year, month)
```

### TimeOffRecord (Existente)
- Mantém estrutura atual
- Relacionado com MonthStatus através de year/month da data

### JornadaArchive (Existente)
- Mantém estrutura atual
- Usado para armazenar registros arquivados

## 🔧 Funções Auxiliares

### `_get_month_status(year, month)`
- Retorna status do mês
- Cria como "aberto" se não existir

### `_can_edit_record(record_date, user_level)`
- Verifica se usuário pode editar registro
- Considera perfil e estado do mês

### `_can_edit_month(year, month, user_level)`
- Verifica se usuário pode editar mês específico
- Considera perfil e estado

### `_get_month_status_display(status)`
- Retorna display amigável do status
- Inclui ícones e cores

## 🛣️ Rotas Principais

### Navegação
- `GET /jornada/` → Redireciona para `/jornada/em-aberto`
- `GET /jornada/em-aberto` → Subpágina EM ABERTO
- `GET /jornada/fechado-revisao` → Subpágina FECHADO PARA REVISÃO
- `GET /jornada/arquivados` → Subpágina ARQUIVADOS

### Transições
- `POST /jornada/mes/<int:year>/<int:month>/fechar` → Fechar mês
- `POST /jornada/mes/<int:year>/<int:month>/confirmar-pagamento` → Confirmar pagamento e arquivar
- `POST /jornada/mes/<int:year>/<int:month>/reabrir` → Reabrir mês (DEV apenas)

### Operações
- `GET /jornada/calendario/<int:year>/<int:month>` → Calendário do mês
- `GET /jornada/feriados/<int:year>/<int:month>` → Feriados do mês (da Escala)

## ⚠️ Regras de Negócio

1. **Mês atual sempre em aberto**: Se não existir status para o mês atual, é criado automaticamente como "aberto"

2. **Proteção de dados arquivados**: ADMIN e OPERADOR não podem editar meses arquivados

3. **Fonte única de feriados**: Feriados são gerenciados apenas na página Escala

4. **Calendário derivado**: Calendário é sempre derivado dos dados da Jornada, não preenchido manualmente

5. **Separação de estados**: Meses arquivados não aparecem em EM ABERTO ou FECHADO

6. **Histórico preservado**: Meses arquivados continuam acessíveis para consulta

## 📝 Documentação de Implementação

Este documento serve como especificação técnica completa do sistema. Qualquer implementação deve seguir rigorosamente estas regras.
