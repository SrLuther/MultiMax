# Otimizações de Performance - MultiMax

## Resumo das Otimizações Implementadas

### 1. Otimização de Queries N+1

#### Dashboard (`multimax/routes/dashboard.py`)
- **Antes**: Loop de 30 queries (uma por dia) para gráfico de recepções
- **Depois**: Uma única query agrupada com `GROUP BY`
- **Ganho**: Redução de 30 queries para 1 query

- **Antes**: Carregava todos os registros de perdas para calcular soma
- **Depois**: Usa `func.sum()` diretamente no SQL
- **Ganho**: Redução de carregamento de dados desnecessários

- **Antes**: Carregava todos os registros de rendimento para calcular média
- **Depois**: Usa `func.avg()` diretamente no SQL
- **Ganho**: Redução de carregamento de dados desnecessários

#### Home (`multimax/routes/home.py`)
- **Antes**: 14 queries (2 por dia x 7 dias) para gráfico de movimentações
- **Depois**: Uma única query agrupada com `GROUP BY` por dia e ação
- **Ganho**: Redução de 14 queries para 1 query

- **Antes**: Múltiplas queries separadas para buscar settings
- **Depois**: Uma única query com `IN` para buscar múltiplos settings
- **Ganho**: Redução de queries repetidas

#### Jornada (`multimax/routes/jornada.py`)
- **Antes**: 4 queries por colaborador (horas, créditos, atribuições, conversões)
- **Depois**: 4 queries agrupadas para todos os colaboradores de uma vez
- **Ganho**: Redução de N*4 queries para 4 queries (onde N = número de colaboradores)

### 2. Índices de Banco de Dados

Adicionados índices nos seguintes campos para melhorar performance de queries frequentes:

#### `Produto`
- `codigo` (já tinha unique, agora indexado)
- `nome`
- `quantidade`
- `estoque_minimo`
- `data_validade`
- `fornecedor_id`
- `categoria`
- `ativo`

#### `Historico`
- `data`
- `product_id`
- `action`

#### `MeatReception`
- `data`
- `fornecedor`
- `tipo`
- `reference_code`
- `recebedor_id`

#### `TemperatureLog`
- `local`
- `data_registro`
- `alerta`

#### `LossRecord`
- `produto_id`
- `data_registro`

#### `ProductLot`
- `reception_id`
- `produto_id`
- `lote_codigo`
- `data_recepcao`
- `data_validade`
- `ativo`

#### `DynamicPricing`
- `produto_id`
- `ativo`
- `data_atualizacao`

### 3. Otimizações de Código

#### Estoque (`multimax/routes/estoque.py`)
- Uso de `set()` para remover duplicatas em listas de IDs
- Uso de dict comprehension ao invés de loops para criar mapeamentos

#### Exportação (`multimax/routes/exportacao.py`)
- Otimização de list comprehensions desnecessárias
- Reutilização de variáveis para evitar recálculos

### 4. Impacto Esperado

#### Redução de Queries
- **Dashboard**: ~30 queries → 1 query (redução de 97%)
- **Home (gráfico)**: 14 queries → 1 query (redução de 93%)
- **Jornada (cards)**: N*4 queries → 4 queries (redução de 100% para N>1)

#### Melhoria de Performance
- Queries com índices serão significativamente mais rápidas
- Menos dados carregados na memória
- Menos round-trips ao banco de dados
- Melhor uso de recursos do servidor

### 5. Próximas Otimizações Sugeridas

1. **Cache**: Implementar cache para queries pesadas que não mudam frequentemente
2. **Paginação**: Garantir que todas as listas grandes usem paginação
3. **Lazy Loading**: Revisar relationships para usar `lazy='select'` ou `lazy='joined'` onde apropriado
4. **Connection Pooling**: Configurar pool de conexões adequado para o banco de dados
5. **Query Optimization**: Revisar queries complexas e adicionar EXPLAIN para análise

### 6. Arquivos Modificados

- `multimax/routes/dashboard.py`
- `multimax/routes/home.py`
- `multimax/routes/jornada.py`
- `multimax/routes/estoque.py`
- `multimax/routes/exportacao.py`
- `multimax/models.py`
- `multimax/optimizations.py` (novo arquivo com utilitários)

### 7. Notas Importantes

- Os índices adicionados melhorarão queries de leitura, mas podem impactar ligeiramente operações de escrita
- Para bancos de dados grandes, considere executar `CREATE INDEX` manualmente ou via migration
- As otimizações de queries agrupadas são especialmente benéficas quando há muitos registros

