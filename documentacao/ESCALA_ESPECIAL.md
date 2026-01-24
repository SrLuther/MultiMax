# 🎯 Sistema de Escalas Especiais - MultiMax v2.8.0+

## Visão Geral

O sistema de **Escalas Especiais** permite gerenciar escalas futuras e especiais para situações como:

- **Limpeza Especial**: Limpeza fora do horário normal (ex: segunda-feira limpeza com todos designados)
- **Feriados**: Horários redistribuídos em feriados (ex: parte da equipe num horário, outra em outro)
- **Redistribuição**: Redistribuição de horários por motivos operacionais
- **Eventos**: Escalas para eventos especiais
- **Manutenção**: Períodos de manutenção ou parada
- **Outros**: Outros tipos de escalas especiais

## Recursos

### 1. **Criar Escalas Especiais**
- **Nome e Descrição**: Identificação clara da escala
- **Tipo**: Limpeza, Feriado, Redistribuição, Evento, Manutenção, Outro
- **Período**: Data de início e fim
- **Turno Customizado**: Horários específicos (ex: 08:00-17:00)
- **Critério de Atribuição**:
  - **Todos**: Aplica a todos os colaboradores ativos
  - **Por Equipe**: Aplica apenas a uma equipe/setor específico
  - **Por Número**: Seleciona N primeiros colaboradores ativos
  - **Manual**: Seleciona colaboradores específicos

### 2. **Gerenciamento de Escalas**
- Visualizar todas as escalas criadas
- Filtrar por status (ativas, futuras, inativas)
- Editar escalas existentes
- Deletar escalas (com confirmação)
- Ativar/desativar escalas

### 3. **Aplicação de Escalas**
- **Aplicar Escala**: Cria/atualiza turnos para os colaboradores selecionados
- **Remover Aplicação**: Deleta os turnos criados pela escala
- Rastreamento de quantos turnos foram criados/removidos

## Acesso

### Página HTML
```
/escala-especial/
```

### APIs REST

#### Listar Escalas
```
GET /api/escala-especial/
GET /api/escala-especial/?ativo=true
GET /api/escala-especial/?tipo=limpeza
GET /api/escala-especial/?data_inicio=2026-01-22
```

#### Criar Escala
```
POST /api/escala-especial/
Content-Type: application/json

{
    "nome": "Limpeza Segunda-Feira",
    "descricao": "Limpeza especial todas as segundas",
    "tipo": "limpeza",
    "data_inicio": "2026-01-27",
    "data_fim": "2026-01-27",
    "turno_customizado": "06:00-14:00",
    "criterio_atribuicao": "todos",
    "ativo": true
}
```

#### Obter Escala
```
GET /api/escala-especial/{id}
```

#### Atualizar Escala
```
PUT /api/escala-especial/{id}
Content-Type: application/json

{
    "nome": "Novo Nome",
    "ativo": false,
    ...
}
```

#### Deletar Escala
```
DELETE /api/escala-especial/{id}
```

#### Tipos Disponíveis
```
GET /api/escala-especial/tipos
```

Resposta:
```json
{
    "status": "success",
    "data": [
        {
            "id": "limpeza",
            "nome": "Limpeza Especial",
            "descricao": "Limpeza fora do horário normal"
        },
        ...
    ]
}
```

#### Critérios de Atribuição
```
GET /api/escala-especial/criterios
```

Resposta:
```json
{
    "status": "success",
    "data": [
        {
            "id": "todos",
            "nome": "Todos os Colaboradores",
            "descricao": "Aplica a toda equipe"
        },
        ...
    ]
}
```

#### Aplicar Escala
```
POST /api/escala-especial/aplicar/{id}
```

Resposta:
```json
{
    "status": "success",
    "message": "Escala aplicada com sucesso! 28 turnos criados/atualizados",
    "turnos_criados": 28
}
```

#### Remover Aplicação
```
POST /api/escala-especial/remover/{id}
```

## Banco de Dados

### Tabela: `escala_especial`

```sql
CREATE TABLE escala_especial (
    id INTEGER PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    tipo VARCHAR(50) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    turno_customizado VARCHAR(100),
    criterio_atribuicao VARCHAR(50) DEFAULT 'todos',
    equipe_id INTEGER,
    numero_pessoas INTEGER,
    colaboradores_selecionados JSON,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em DATETIME,
    atualizado_em DATETIME,
    criado_por VARCHAR(100),
    
    FOREIGN KEY (equipe_id) REFERENCES setor(id)
);
```

### Campos

- **id**: Identificador único
- **nome**: Nome da escala (ex: "Limpeza Segunda-Feira")
- **descricao**: Descrição detalhada (opcional)
- **tipo**: Tipo de escala (limpeza, feriado, redistribuicao, evento, manutencao, outro)
- **data_inicio**: Data de início da escala
- **data_fim**: Data de fim da escala
- **turno_customizado**: Horário customizado (ex: "08:00-17:00", opcional)
- **criterio_atribuicao**: Como a escala é atribuída (todos, por_equipe, por_numero, manual)
- **equipe_id**: ID da equipe (se criterio for 'por_equipe')
- **numero_pessoas**: Número de pessoas (se criterio for 'por_numero')
- **colaboradores_selecionados**: JSON array com IDs dos colaboradores (se criterio for 'manual')
- **ativo**: Se a escala está ativa
- **criado_em**: Data/hora de criação
- **atualizado_em**: Data/hora da última atualização
- **criado_por**: Usuário que criou a escala

## Fluxo de Uso

### 1. Criar Escala
1. Acesse `/escala-especial/`
2. Clique em "Nova Escala Especial"
3. Preencha os campos:
   - Nome: "Limpeza Segunda-Feira"
   - Tipo: Limpeza
   - Data Início: 27/01/2026
   - Data Fim: 27/01/2026
   - Turno: 06:00-14:00
   - Critério: Todos
4. Clique em "Criar Escala"

### 2. Aplicar Escala
1. Encontre a escala criada
2. Clique no botão "Aplicar"
3. Confirme a ação
4. Os turnos serão criados para todos os colaboradores selecionados
5. Você verá uma confirmação: "Escala aplicada com sucesso! X turnos criados/atualizados"

### 3. Remover Aplicação
1. Encontre a escala aplicada
2. Clique no botão "Remover"
3. Confirme a ação
4. Os turnos criados pela escala serão deletados

### 4. Editar Escala
1. Encontre a escala
2. Clique em "Editar"
3. Modifique os campos desejados
4. Clique em "Salvar Alterações"

## Exemplos de Uso

### Exemplo 1: Limpeza Especial (Todos os Colaboradores)

```json
{
    "nome": "Limpeza Geral - Segundo-feira",
    "descricao": "Limpeza geral com toda equipe no segundo-feira",
    "tipo": "limpeza",
    "data_inicio": "2026-02-03",
    "data_fim": "2026-02-03",
    "turno_customizado": "06:00-14:00",
    "criterio_atribuicao": "todos",
    "ativo": true
}
```

**Resultado**: Todos os colaboradores ativos receberão turno de limpeza nessa data.

### Exemplo 2: Feriado com Redistribuição (Por Equipe)

```json
{
    "nome": "Carnaval - Turma A",
    "descricao": "Horário alterado para Carnaval - Turma A",
    "tipo": "feriado",
    "data_inicio": "2026-02-10",
    "data_fim": "2026-02-12",
    "turno_customizado": "08:00-16:00",
    "criterio_atribuicao": "por_equipe",
    "equipe_id": 1,
    "ativo": true
}
```

**Resultado**: Apenas colaboradores da equipe 1 receberão esse turno especial.

### Exemplo 3: Seleção Manual

```json
{
    "nome": "Treinamento Especial - Grupo A",
    "descricao": "Treinamento de segurança para grupo selecionado",
    "tipo": "evento",
    "data_inicio": "2026-01-30",
    "data_fim": "2026-01-30",
    "turno_customizado": "14:00-18:00",
    "criterio_atribuicao": "manual",
    "colaboradores_selecionados": [1, 3, 5, 7],
    "ativo": true
}
```

**Resultado**: Apenas os colaboradores com IDs 1, 3, 5 e 7 receberão esse turno.

## Integração com Sistema de Turnos

As escalas especiais criam/atualizam entradas na tabela `shift`:

- **collaborator_id**: ID do colaborador
- **date**: Data do turno
- **shift_type**: Tipo de turno (usa o turno_customizado ou "especial")
- **turno**: Turno customizado ou "Especial"
- **descricao**: Contém tag como "[LIMPEZA] Nome da Escala"

Isso permite que o sistema de escala visualize e interprete corretamente os turnos especiais criados.

## Migração

Para aplicar as mudanças do banco de dados:

```bash
cd one-time-migrations
python 2026_01_22_create_escala_especial.py
```

Ou executar via Flask:

```bash
python -c "from multimax import create_app, db; app = create_app(); db.create_all()"
```

## Notas Importantes

1. **Turnos Existentes**: Se um colaborador já tiver um turno na data, ele será **atualizado**, não criado novamente
2. **Remoção**: A remoção de aplicação deleta apenas turnos que contêm a tag `[TIPO]` no campo descrição
3. **Ativo/Inativo**: Desativar uma escala não remove os turnos já criados
4. **Datas**: Data início deve ser ≤ Data fim
5. **Colaboradores**: Apenas colaboradores com `ativo=true` são considerados

## Próximas Melhorias

- [ ] Visualização dos colaboradores que serão afetados antes de aplicar
- [ ] Histórico de aplicações/remoções de escalas
- [ ] Templates de escalas recorrentes
- [ ] Notificações para colaboradores afetados
- [ ] Exportação de escalas especiais
- [ ] Dashboard de escalas por colaborador
- [ ] Validação de conflitos com férias/folgas
