# Sistema de Saldo de Horas - Documentação

## Visão Geral

O sistema de saldo de horas foi implementado para gerenciar horas restantes (não convertidas em dias completos) entre ciclos mensais. Isso permite que pequenas quantidades de horas sejam carregadas para o próximo mês, onde podem se somar a novas horas lançadas.

## Conceitos Principais

### Horas vs Dias
- **1 dia = 8 horas**
- Exemplo: Se um colaborador lançou 9.5 horas no mês:
  - **Dias completos**: 1 dia (8 horas) → Pago em R$
  - **Horas restantes**: 1.5 horas → Transportado para próximo mês

### Saldo
O saldo é o resto da divisão `total_horas % 8`. Exemplos:
- 8.0h → 0 horas de saldo (1 dia completo)
- 9.5h → 1.5 horas de saldo
- 16.0h → 0 horas de saldo (2 dias completos)
- 7.5h → 7.5 horas de saldo (sem dias completos)
- 15.5h → 7.5 horas de saldo (1 dia completo + 7.5h)

## Fluxo de Operação

### 1. Durante o Ciclo Mensal (Ativo)
- Colaboradores lançam horas normalmente
- Horas são armazenadas em `Ciclo.valor_horas`
- Sistema mantém histórico de todas as horas em **horas reais** (sem conversão)

### 2. Fechamento do Ciclo (Registrar Pagamento)
Quando o administrador clica em "Registrar Pagamento":

1. **Cálculo de Saldos**: Sistema calcula `saldo = total_horas % 8` para cada colaborador
2. **Armazenamento**: Saldos são salvos na tabela `ciclo_saldo` com:
   - `collaborator_id`: ID do colaborador
   - `mes_ano`: Mês em formato "MM-YYYY"
   - `saldo`: Valor em horas
   - `created_at`, `created_by`, `updated_at`, `updated_by`: Auditoria

3. **Carryover**: Horas restantes > 0 são automaticamente lançadas como "Carryover" no próximo mês
4. **Pagamento**: Apenas dias completos são pagos em R$

### 3. Próximo Ciclo (Aplicação de Saldo)
Ao iniciar novo mês:
- Saldo anterior é recuperado da tabela `ciclo_saldo`
- Saldo é aplicado para compensar:
  - **Saldo positivo** (ex: +1.5h): Horas extras adicionadas
  - **Saldo negativo** (ex: -2.0h): Horas faltantes deduzidas

## Tabelas do Banco de Dados

### Tabela: `ciclo_saldo`
```sql
CREATE TABLE ciclo_saldo (
    id INTEGER PRIMARY KEY,
    collaborator_id INTEGER NOT NULL FK(collaborator.id),
    mes_ano VARCHAR(7) NOT NULL,  -- Formato: "01-2026", "02-2026", etc
    saldo NUMERIC(5,1) NOT NULL DEFAULT 0,  -- Em horas
    created_at DATETIME NOT NULL,
    created_by VARCHAR(100),
    updated_at DATETIME,
    updated_by VARCHAR(100),
    UNIQUE (collaborator_id, mes_ano)
);
```

## Funções do Serviço (`ciclo_saldo_service.py`)

### 1. `calcular_saldo_mensal(total_horas: float) -> float`
Calcula resto da divisão por 8.
```python
saldo = calcular_saldo_mensal(9.5)  # Retorna: 1.5
```

### 2. `registrar_saldo(collaborator_id, mes_ano, saldo, usuario) -> CicloSaldo`
Registra ou atualiza saldo no banco.
```python
saldo_record = registrar_saldo(
    collaborator_id=1,
    mes_ano="01-2026",
    saldo=1.5,
    usuario="admin"
)
```

### 3. `obter_saldo_anterior(collaborator_id, data_referencia) -> float`
Obtém saldo do mês anterior.
```python
saldo_anterior = obter_saldo_anterior(collaborator_id=1)  # Retorna: 1.5
```

### 4. `resumo_em_dias_e_horas(total_horas: float) -> str`
**Função de exibição visual** (não altera dados). Converte horas para formato legível.
```python
resumo_em_dias_e_horas(9.5)   # "1 dia e 1h30min"
resumo_em_dias_e_horas(16.0)  # "2 dias"
resumo_em_dias_e_horas(7.5)   # "7h30min"
resumo_em_dias_e_horas(-8.0)  # "-1 dia"
```

### 5. `fechar_ciclo_mensal(colaboradores_totais, mes_ano, usuario) -> dict`
Função principal chamada ao fechar ciclo. Calcula e armazena saldos de todos os colaboradores.
```python
resultado = fechar_ciclo_mensal(
    colaboradores_totais={...},
    mes_ano="01-2026",
    usuario="admin"
)
```

### 6. `aplicar_saldos_anteriores_ciclo_novo(colaboradores_ids, novo_mes_ano) -> dict`
Retorna informações sobre saldos anteriores (apenas leitura, não modifica).
```python
info = aplicar_saldos_anteriores_ciclo_novo(
    colaboradores_ids=[1, 2, 3],
    novo_mes_ano="02-2026"
)
# Resultado:
# {
#     "novo_mes": "02-2026",
#     "mes_anterior": "01-2026",
#     "saldos_aplicaveis": [...],
#     "total_saldo_anterior": 15.5
# }
```

### 7. `gerar_relatorio_saldos(mes_ano) -> dict`
Gera relatório de saldos para auditoria.
```python
relatorio = gerar_relatorio_saldos(mes_ano="01-2026")
# Resultado:
# {
#     "mes_ano": "01-2026",
#     "saldos": [...],
#     "total_saldo": 25.5,
#     "colaboradores_com_saldo": 5
# }
```

## Interface do Usuário

### Modal de Fechamento (Registrar Pagamento)
Ao abrir modal de fechamento, o usuário vê:

1. **Tabela de Resumo**: Mostra horas totais, dias completos, horas restantes e valor
2. **Avisos**: Lista colaboradores com < 8h de horas (não entram em dias completos)
3. **Novo: Seção de Saldos** (ℹ️ INFO):
   - Mostra saldo que será registrado para próximo mês
   - Exibe em formato visual: "+1.5h (1h30min)"
   - Aviso informativo sobre aplicação automática

### Exemplo de Exibição

```
📋 Resumo do Ciclo

Colaborador    | Horas Totais | Dias | Restantes | Valor
─────────────────────────────────────────────────────────
João Silva     |    9.5h      |  1   |    1.5h   | R$ 150.00
Maria Santos   |   16.0h      |  2   |    0.0h   | R$ 300.00
─────────────────────────────────────────────────────────
TOTAL          |   25.5h      |  3   |    1.5h   | R$ 450.00

ℹ️ Saldos de Horas para o Próximo Mês (01-2026):
   • João Silva: +1.5h (1h30min)
   • Maria Santos: 0h (Sem saldo)

✅ Estes saldos serão aplicados automaticamente no próximo ciclo...
```

## Integração com Ciclos

### Fluxo de Fechamento em `ciclos.py`

1. **Rota**: `/ciclos/fechamento/confirmar` (POST)
2. **Função**: `confirmar_fechamento()`
3. **Passos**:
   ```python
   # 1. Agrupar registros por colaborador
   colaboradores_totais, totais_gerais = _agrupar_e_calcular_totais(registros_ativos)
   
   # 2. Criar carryover (transportar horas)
   _criar_carryover_e_fechar_registros(...)
   
   # 3. Fechar folgas e ocorrências
   _fechar_folgas_e_ocorrencias(...)
   
   # 4. Arquivar ciclos semanais
   _arquivar_ciclos_semanais(...)
   
   # 5. 🆕 Registrar saldos
   _registrar_fechamento_e_log(
       proximo_ciclo_id,
       totais_gerais,
       colaboradores_totais  # ← Novo parâmetro
   )
   ```

## Histórico vs Exibição

**Importante**: O histórico de horas permanece **sempre em horas reais**.

- **Histórico (Banco de Dados)**: 9.5h
- **Exibição (Tela/PDF)**: "1 dia e 1h30min"
- **Página Anterior**: 9.5h (horas reais, sem conversão)

A conversão em "dias e horas" é **apenas visual** para facilitar leitura. Os dados sempre são mantidos em horas reais para precisão.

## Relatórios e PDFs

### PDF de Ciclos
Os PDFs gerados mostram:
- Horas reais no histórico
- Saldo visual em formato "X dias e Y horas"
- Informações de carryover

### Relatório de Saldos
Acessível via:
```
/ciclos/relatorio_saldos?mes_ano=01-2026
```

Mostra:
- Saldo de cada colaborador
- Saldo visual
- Total geral
- Data de criação e quem registrou

## Casos de Uso

### Caso 1: Colaborador com Horas Extras
```
Mês 1:
- Lançado: 17h
- Dias completos: 2 dias → R$ 300.00
- Saldo: 1h → Carryover para mês 2

Mês 2:
- Saldo anterior: +1h
- Novas horas: 7h
- Total: 8h (1 dia) → R$ 150.00
- Saldo novo: 0h
```

### Caso 2: Colaborador com Horas Faltantes
```
Mês 1:
- Lançado: 6h
- Dias completos: 0 dias
- Saldo: -2h (dívida)

Mês 2:
- Saldo anterior: -2h
- Novas horas: 10h
- Total: 8h (1 dia) → R$ 150.00
- Saldo novo: 0h
```

### Caso 3: Acúmulo de Horas
```
Mês 1: Saldo 1.5h
Mês 2: Saldo 2.0h (acumulado: 3.5h)
Mês 3: Saldo 2.5h (acumulado: 6.0h)
Mês 4: Novas horas 2h + 6h saldo = 8h (1 dia pago)
```

## Auditoria e Logs

Cada operação de saldo é registrada:
- **Criação**: `ciclo_saldo.created_at`, `created_by`
- **Atualização**: `ciclo_saldo.updated_at`, `updated_by`
- **Log de Sistema**: `system_log` com evento `saldo_horas_registrado`

Exemplo de log:
```
Evento: saldo_horas_registrado
Origem: Ciclos
Detalhes: Saldos de horas registrados para o mês 01-2026: 
          João Silva: 1h30min; Maria Santos: Sem saldo
Usuário: admin
Data: 2026-01-23 15:30:45
```

## Validações e Regras

1. **Unicidade**: Um saldo por colaborador por mês (`UNIQUE (collaborator_id, mes_ano)`)
2. **Saldo Mínimo**: Saldo pode ser negativo (dívida de horas)
3. **Carryover Automático**: Horas > 0 e < 8 são automaticamente lançadas
4. **Apenas Exibição**: Conversão "dias e horas" é apenas visual

## Troubleshooting

### Problema: Saldo não está sendo registrado
- Verificar se a tabela `ciclo_saldo` foi criada
- Executar migration: `python one-time-migrations/2026_01_23_create_ciclo_saldo.py`
- Verificar logs de sistema para erros

### Problema: Saldo visual incorreto
- A função `resumo_em_dias_e_horas()` é determinística
- Verificar valor armazenado em `ciclo_saldo.saldo`
- Exemplo: 9.5 → "1 dia e 1h30min" (sempre)

### Problema: Carryover não está sendo criado
- Verificar se `_criar_carryover_e_fechar_registros()` foi executado
- Verificar se horas restantes > 0 e < 8
- Verificar logs de sistema

## Roadmap Futuro

- [ ] Dashboard com visualização de saldos por colaborador
- [ ] Previsão de compensação de saldos
- [ ] Alertas para saldos acumulados > 40h
- [ ] Relatório de saldos em PDF
- [ ] Export de saldos para folha de pagamento
