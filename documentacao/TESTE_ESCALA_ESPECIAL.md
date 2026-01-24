# 🧪 Testes do Sistema de Escalas Especiais

## Checklist de Testes

### 1. Interface Visual (HTML/JavaScript)

- [ ] Página carrega sem erros (`/escala-especial/`)
- [ ] Abas de filtro funcionam (Todas, Ativas, Futuras)
- [ ] Modal de nova escala abre corretamente
- [ ] Campos de formulário são validados
- [ ] Seleção de tipo preenche o select
- [ ] Seleção de critério mostra/esconde campos opcionais
- [ ] Cards de escalas são renderizados corretamente
- [ ] Botões de ação funcionam (Editar, Aplicar, Deletar)

### 2. Operações CRUD

#### Criar Escala Especial ✓
```bash
curl -X POST http://localhost:5000/api/escala-especial/ \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Teste Limpeza",
    "tipo": "limpeza",
    "data_inicio": "2026-01-27",
    "data_fim": "2026-01-27",
    "turno_customizado": "06:00-14:00",
    "criterio_atribuicao": "todos"
  }'
```

- [ ] Resposta retorna 201 Created
- [ ] Dados são salvos no banco
- [ ] ID é gerado automaticamente
- [ ] Timestamps são preenchidos

#### Listar Escalas ✓
```bash
curl http://localhost:5000/api/escala-especial/
```

- [ ] Retorna lista de escalas
- [ ] Filtro por ativo funciona: `?ativo=true`
- [ ] Filtro por tipo funciona: `?tipo=limpeza`
- [ ] Filtro por data funciona: `?data_inicio=2026-01-27`

#### Obter Escala ✓
```bash
curl http://localhost:5000/api/escala-especial/{id}
```

- [ ] Retorna detalhes completos da escala
- [ ] Retorna 404 para ID inexistente

#### Atualizar Escala ✓
```bash
curl -X PUT http://localhost:5000/api/escala-especial/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Escala Atualizada",
    "ativo": false
  }'
```

- [ ] Atualiza campos corretamente
- [ ] Timestamp de atualização é modificado
- [ ] Dados antigos não são sobrescrittos desnecessariamente

#### Deletar Escala ✓
```bash
curl -X DELETE http://localhost:5000/api/escala-especial/{id}
```

- [ ] Escala é removida do banco
- [ ] Retorna 200 OK
- [ ] ID inexistente retorna 404

### 3. Funcionalidades Especiais

#### Tipos de Escala ✓
```bash
curl http://localhost:5000/api/escala-especial/tipos
```

- [ ] Retorna 6 tipos: limpeza, feriado, redistribuicao, evento, manutencao, outro
- [ ] Cada tipo tem id, nome, descricao

#### Critérios de Atribuição ✓
```bash
curl http://localhost:5000/api/escala-especial/criterios
```

- [ ] Retorna 4 critérios: todos, por_equipe, por_numero, manual
- [ ] Cada critério tem id, nome, descricao

#### Aplicar Escala ✓
```bash
curl -X POST http://localhost:5000/api/escala-especial/aplicar/{id}
```

- [ ] Turnos são criados para o período inteiro
- [ ] Colaboradores selecionados recebem os turnos
- [ ] Resposta indica quantos turnos foram criados
- [ ] Turnos contêm tag `[TIPO]` na descrição
- [ ] Turnos existentes são atualizados (não duplicados)

#### Remover Aplicação ✓
```bash
curl -X POST http://localhost:5000/api/escala-especial/remover/{id}
```

- [ ] Turnos criados pela escala são removidos
- [ ] Resposta indica quantos turnos foram removidos
- [ ] Apenas turnos com tag da escala são removidos

### 4. Validações

#### Campos Obrigatórios
- [ ] Nome: erro se vazio
- [ ] Tipo: erro se vazio
- [ ] Data Início: erro se vazio
- [ ] Data Fim: erro se vazio
- [ ] Critério: erro se vazio

#### Validações de Data
- [ ] Data início > data fim: erro
- [ ] Formato de data inválido: erro
- [ ] Datas no passado: permitidas (para edição)

#### Validações de Critério
- [ ] Critério "por_equipe": exige equipe_id
- [ ] Critério "por_numero": exige numero_pessoas > 0
- [ ] Critério "manual": exige colaboradores_selecionados não vazio

### 5. Banco de Dados

- [ ] Tabela `escala_especial` existe
- [ ] Coluna `id` é primary key
- [ ] Coluna `data_inicio` é indexed
- [ ] Coluna `ativo` é indexed
- [ ] Coluna `tipo` é indexed
- [ ] Foreign key `equipe_id` referencia `setor`
- [ ] Campo `colaboradores_selecionados` armazena JSON
- [ ] Timestamps são datetime com timezone

### 6. Integração com Turnos (Shift)

- [ ] Turnos criados têm `collaborator_id` correto
- [ ] Turnos têm `date` correto (por cada dia do período)
- [ ] Campo `shift_type` é preenchido
- [ ] Campo `descricao` contém `[TIPO]` e nome da escala
- [ ] Turnos aparecem na visualização de escala
- [ ] Remover escala remove os turnos

### 7. Casos de Uso Reais

#### Caso 1: Limpeza todas as segundas (Todos)
```json
{
    "nome": "Limpeza Semanal Segunda",
    "tipo": "limpeza",
    "data_inicio": "2026-02-02",
    "data_fim": "2026-02-02",
    "turno_customizado": "06:00-14:00",
    "criterio_atribuicao": "todos"
}
```

- [ ] Todos os colaboradores recebem o turno
- [ ] Turno aparece no sistema de escala

#### Caso 2: Feriado com equipe dividida (Por Equipe)
```json
{
    "nome": "Carnaval - Turma A",
    "tipo": "feriado",
    "data_inicio": "2026-02-10",
    "data_fim": "2026-02-10",
    "turno_customizado": "08:00-16:00",
    "criterio_atribuicao": "por_equipe",
    "equipe_id": 1
}
```

- [ ] Apenas colaboradores da equipe 1 recebem
- [ ] Colaboradores de outras equipes não recebem

#### Caso 3: Seleção manual (Manual)
```json
{
    "nome": "Treinamento Especial",
    "tipo": "evento",
    "data_inicio": "2026-01-30",
    "data_fim": "2026-01-30",
    "turno_customizado": "14:00-18:00",
    "criterio_atribuicao": "manual",
    "colaboradores_selecionados": [1, 2, 3]
}
```

- [ ] Apenas colaboradores 1, 2, 3 recebem
- [ ] Ordem não importa

### 8. Performance

- [ ] Listar 100+ escalas é rápido (< 1s)
- [ ] Aplicar escala com 20+ colaboradores é rápido (< 5s)
- [ ] Buscar escala por ID é rápido (< 100ms)
- [ ] Sem N+1 queries

### 9. Segurança

- [ ] Acesso requer autenticação (@login_required)
- [ ] Usuário não autenticado recebe 401 Unauthorized
- [ ] SQL injection não é possível (parameterized queries)
- [ ] XSS protegido no JavaScript
- [ ] CSRF protegido (se aplicável)

### 10. Edge Cases

- [ ] Escala de 1 dia: funciona
- [ ] Escala de 30+ dias: funciona
- [ ] Colaborador com ID não encontrado: graceful error
- [ ] Equipe com ID não encontrado: graceful error
- [ ] Número de pessoas > total de colaboradores: usa apenas disponíveis
- [ ] Remover escala não aplicada: sem erro

## Teste Manual Completo

### Preparação
1. Limpar banco de testes (ou usar dev)
2. Criar alguns colaboradores
3. Criar 2-3 setores/equipes

### Fluxo 1: Limpeza Especial
1. Ir para `/escala-especial/`
2. Clique "Nova Escala Especial"
3. Preencha:
   - Nome: "Limpeza Geral"
   - Tipo: Limpeza
   - Data: 27/01/2026 a 27/01/2026
   - Turno: 06:00-14:00
   - Critério: Todos
4. Clique Criar
5. Veja a escala na lista
6. Clique Aplicar
7. Veja a mensagem: "X turnos criados"
8. Verifique no sistema de escala se os turnos aparecem

### Fluxo 2: Editar Escala
1. Clique Editar na escala criada
2. Mude nome para "Limpeza Geral - Editada"
3. Clique Salvar
4. Veja a mudança refletida na lista

### Fluxo 3: Remover Aplicação
1. Encontre a escala aplicada
2. Clique Remover (novo botão ou opção)
3. Veja a mensagem: "X turnos removidos"
4. Verifique no sistema de escala se os turnos sumiram

### Fluxo 4: Deletar Escala
1. Clique Deletar na escala
2. Confirme
3. Veja a escala desaparecer da lista

## Testes de Integração (pytest)

```python
def test_criar_escala_especial(client, auth_token):
    response = client.post('/api/escala-especial/', 
        json={
            'nome': 'Teste',
            'tipo': 'limpeza',
            'data_inicio': '2026-01-27',
            'data_fim': '2026-01-27',
            'criterio_atribuicao': 'todos'
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 201
    assert response.json['status'] == 'success'

def test_aplicar_escala(client, auth_token, escala_id):
    response = client.post(f'/api/escala-especial/aplicar/{escala_id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    assert response.json['turnos_criados'] > 0
```

## Checklist Final

- [ ] Todos os testes CRUD funcionam
- [ ] Aplicar/Remover escalas funciona
- [ ] Validações funcionam
- [ ] Banco de dados está correto
- [ ] Integração com turnos funciona
- [ ] Interface HTML está responsiva
- [ ] Sem erros no console (JavaScript/Python)
- [ ] Documentação está completa
- [ ] README foi atualizado
- [ ] Migração foi executada com sucesso

## Próximos Passos

1. Executar migração do banco
2. Rodar testes manuais completos
3. Verificar logs de erro
4. Otimizar queries se necessário
5. Adicionar cache se necessário
6. Documentar em CHANGELOG.md
