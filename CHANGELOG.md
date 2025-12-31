# Changelog — MultiMax

## [2.2] - 2025-01-XX

### ⚡ Otimizações de Performance

#### Redução de Queries N+1
- **Dashboard**: Otimização de queries para gráfico de recepções - redução de ~30 queries para 1 query (97% de redução)
- **Home**: Otimização de gráfico de movimentações - redução de 14 queries para 1 query (93% de redução)
- **Jornada**: Otimização de queries para cards de colaboradores - redução de N*4 queries para 4 queries
- **Estoque**: Uso de agregações SQL diretas (func.sum, func.avg) ao invés de carregar todos os registros
- **Exportação**: Otimizações de list comprehensions e reutilização de variáveis

#### Índices de Banco de Dados
Adicionados índices estratégicos nos seguintes modelos para melhorar performance:
- `Produto`: código, nome, quantidade, estoque_minimo, data_validade, fornecedor_id, categoria, ativo
- `Historico`: data, product_id, action
- `MeatReception`: data, fornecedor, tipo, reference_code, recebedor_id
- `TemperatureLog`: local, data_registro, alerta
- `LossRecord`: produto_id, data_registro
- `ProductLot`: reception_id, produto_id, lote_codigo, data_recepcao, data_validade, ativo
- `DynamicPricing`: produto_id, ativo, data_atualizacao

#### Novos Utilitários
- Criado arquivo `multimax/optimizations.py` com funções utilitárias para cache de datas

### 📝 Documentação
- Adicionado arquivo `OTIMIZACOES.md` documentando todas as otimizações implementadas

### 🐛 Correções
- Melhorias gerais de performance e otimização de queries
- Correções de lint em diversos arquivos

---

## [2.0] - 2025-01-XX

### 🎉 Novas Funcionalidades

#### Gestão de Açougue e Câmara Fria
- **Cortes de Carne**: Sistema completo de cadastro e execução de cortes com cálculo automático de rendimento
- **Controle de Lotes**: Rastreabilidade completa por lote com histórico de movimentações
- **Maturação de Carnes**: Controle de maturação com alertas de tempo e temperatura
- **Rendimento**: Análise automática de rendimento por recepção
- **Câmara Fria**: Dashboard de ocupação com controle de capacidade e temperatura
- **Integração Temperatura × Estoque**: Bloqueio automático de produtos quando temperatura está fora da faixa

#### Precificação e Aproveitamento
- **Precificação Dinâmica**: Ajuste automático de preços baseado em validade e demanda
- **Aproveitamento**: Sugestões inteligentes para produtos próximos ao vencimento

#### Certificados e Avaliações
- **Certificados Sanitários**: Controle completo de certificados e validades
- **Certificados de Temperatura**: Geração automática de certificados para fiscalização
- **Avaliação de Fornecedores**: Sistema de notas (qualidade, preço, pontualidade, atendimento)

#### Dashboard e Análises
- **Dashboard Executivo**: Visão geral com KPIs, gráficos e métricas importantes
- **Alertas de Temperatura**: Sistema de alertas que bloqueia produtos automaticamente

### 🔧 Melhorias

#### Responsividade e Mobile
- Arquivo `mobile-fixes.css` criado com correções específicas para dispositivos móveis
- Tabelas responsivas com scroll horizontal suave
- Formulários otimizados para touch (font-size 16px previne zoom no iOS)
- Botões com tamanho mínimo de 44px (padrão de acessibilidade)
- Navegação mobile-friendly com sidebar e overlay
- Safe area para dispositivos com notch
- Media queries para tablets e smartphones

#### Segurança e Permissões
- Usuário `DEV` com acesso completo a todas as funcionalidades
- Apenas `DEV` pode gerenciar administradores (criar, editar, excluir)
- Usuários `visualizador` bloqueados de fazer alterações (exceto nome e senha no perfil)
- Validação de permissões em todas as rotas POST

#### Interface
- Avisos de "Página em Construção" adicionados em 18 páginas
- Menu lateral atualizado com novos módulos
- Melhorias visuais e de UX

### 📦 Novos Modelos de Banco de Dados
- `MeatCut` - Cadastro de tipos de cortes
- `MeatCutExecution` - Execução de cortes
- `MeatMaturation` - Controle de maturação
- `ProductLot` - Controle de lotes
- `LotMovement` - Movimentações de lotes
- `TemperatureProductAlert` - Alertas de temperatura
- `DynamicPricing` - Precificação dinâmica
- `PricingHistory` - Histórico de preços
- `WasteUtilization` - Sugestões de aproveitamento
- `ColdRoomOccupancy` - Ocupação da câmara fria
- `TraceabilityRecord` - Rastreabilidade completa
- `SupplierEvaluation` - Avaliação de fornecedores
- `SanitaryCertificate` - Certificados sanitários
- `TemperatureCertificate` - Certificados de temperatura
- `YieldAnalysis` - Análise de rendimento

### 🐛 Correções
- Correção de permissões para usuário DEV em todas as páginas
- Bloqueio de saída de produtos quando há alerta de temperatura ativo
- Melhorias na validação de entrada de dados
- Correções de responsividade em templates

### 📝 Documentação
- `RESPONSIVIDADE.md` - Documentação completa sobre responsividade mobile
- CHANGELOG atualizado com todas as mudanças

### 🗑️ Removido
- Pasta `.trae` (não necessária)
- Scripts antigos de deploy e verificação

---

## [1.0.0] - 2025-12-11

### Ajustes de Tabelas nos Relatórios de Carnes

Principais mudanças aplicadas aos PDFs de relatório diário e semanal:

- Fonte das células reduzida para 8 e espaçamento de linha (leading) ajustado para 10, aumentando a densidade sem perder legibilidade.
- Larguras das colunas calculadas dinamicamente com base na largura útil da página para evitar vazamento de conteúdo:
  - Data/Hora: 1.2 in
  - Ref.: 0.9 in
  - Total (kg): 1.2 in
  - Recebedor: 1.5 in (ajustada automaticamente se necessário)
  - Fornecedor: ocupa o restante, com mínimo de 1.2 in
- Cabeçalho encurtado de "Total líquido (kg)" para "Total (kg)" para prevenir overflow visual e padronizar nomenclatura.
- Alinhamento à direita mantido na coluna de Totais; cabeçalho com fonte 8 para consistência visual.
- Quebra de linha em células (`wordWrap='LTR'`) para textos mais longos em Fornecedor e Recebedor sem ultrapassar os limites da tabela.

Ajustes complementares relacionados:

- Compatibilidade de timezone no cálculo de intervalos (diário/semanal) com `datetime.combine(...).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))` para suportar Python anteriores ao 3.11.
- Correções de linter: uso de aliases `CleaningTaskModel` e `CleaningHistoryModel` nas rotas de exportação para evitar conflitos de símbolo.
- UI de Carnes: remoção de `_now_br` no template, passando `today_str` pela rota; largura do filtro "Tipo" ampliada para 360px para evitar truncamento do conteúdo.
