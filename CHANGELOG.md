# Changelog — MultiMax

## [2.3.5] - 2025-01-04

### 🔧 Correções

#### Banco de Dados SQLite
- **Caminho Absoluto do Banco de Dados**: Corrigida lógica de definição do caminho do banco SQLite
  - Agora usa caminho absoluto fixo, eliminando dependência do diretório de execução
  - Prioridade: variável de ambiente `DB_FILE_PATH` > padrão `/opt/multimax/multimax-data/estoque.db`
  - Funciona tanto dentro quanto fora do Docker
  - Garante que o diretório do banco seja criado automaticamente se não existir
  - Mantém compatibilidade com configurações existentes via variáveis de ambiente

---

## [2.3.4] - 2025-01-04

### 🔧 Correções

#### Docker Compose
- **Volume Persistente na VPS**: Corrigido caminho do volume para apontar para diretório persistente
  - Alterado de `./data:/app/data` para `/opt/multimax/multimax-data/:/app/data`
  - Garante persistência dos dados na VPS mesmo após atualizações do container

---

## [2.3.3] - 2025-01-04

### 🎉 Novas Funcionalidades

#### Sistema de Valores na Jornada
- **Cards de Valores a Receber**: Sistema completo de cálculo e exibição de valores monetários
  - **Card 1 - Valor Dias Completos (Individual)**: Exibe o valor referente aos dias completos de um colaborador (dias × valor por dia)
  - **Card 2 - Valor Dias + Horas (Individual)**: Exibe o valor referente às horas parciais (< 8h) calculadas proporcionalmente
  - **Card 3 - Valor Total Individual**: Soma dos valores dos cards 1 e 2, mostrando o valor final que o colaborador tem a receber
  - **Card 4 - Valor Total Geral**: Soma o valor de todos os colaboradores, incluindo dias completos e horas parciais
- **Modal de Configurações**: Interface para configurar o valor por dia completo (x)
  - Botão "Configurações" no header dos cards
  - Validação de entrada (valor deve ser positivo)
  - Atualização automática dos cards após salvar
  - Log de alterações no sistema
- **Cálculo Proporcional**: Horas parciais (< 8h) são calculadas proporcionalmente ao valor de x
  - Fórmula: (horas ÷ 8h) × valor por dia
  - Suporte a filtros de data (início e fim)
- **Atualização Automática**: Cards atualizam automaticamente quando:
  - O valor por dia é alterado
  - Os dados de dias e horas dos colaboradores mudam
  - Filtros de data são aplicados

### 📝 Arquivos Modificados
- `multimax/routes/jornada.py`: 
  - Adicionadas funções `_get_day_value()`, `_calculate_collaborator_values()`, `_calculate_total_values()`
  - Novas rotas `GET/POST /jornada/config/valor-dia` para configuração
  - Importação do modelo `AppSetting` para armazenar configuração
  - Atualização da rota `index()` para calcular e passar valores para o template
- `templates/jornada/index.html`: 
  - Adicionados 4 cards de valores com design moderno e responsivo
  - Modal de configurações para valor por dia
  - CSS completo para estilização dos cards (suporte a tema dark)
  - JavaScript para carregar/salvar configuração e atualização automática

### 🔧 Melhorias Técnicas
- **Armazenamento de Configuração**: Uso do modelo `AppSetting` para persistir o valor por dia
- **Cálculos Eficientes**: Funções otimizadas para calcular valores considerando filtros de data
- **Interface Responsiva**: Cards adaptáveis para diferentes tamanhos de tela
- **Validações Robustas**: Validação de entrada e tratamento de erros

---

## [2.3.2] - 2025-01-04

### 🔧 Melhorias

#### Monitoramento de Saúde do Sistema
- **Verificação do Nginx com Hostname Real**: Atualização da função `_check_nginx_health()` para usar hostname real
  - Substituído `127.0.0.1` por `multimax.tec.br` em todas as verificações
  - Verifica portas 80 (HTTP) e 443 (HTTPS) usando o hostname real
  - Detecta redirecionamentos HTTP → HTTPS através do hostname real
  - Mantém compatibilidade total com dashboard `/db`

### 📝 Arquivos Modificados
- `multimax/routes/dbadmin.py`: 
  - Função `_check_nginx_health()` atualizada para usar `multimax.tec.br`
  - Testes de porta e requisições HTTP agora usam hostname real

---

## [2.3.1] - 2025-01-04

### 🔧 Melhorias

#### Monitoramento de Saúde do Sistema
- **Verificação Aprimorada do Nginx**: Melhorias na função `_check_nginx_health()` para verificação mais robusta
  - Agora verifica tanto a porta 80 (HTTP) quanto a porta 443 (HTTPS)
  - Detecta automaticamente redirecionamentos HTTP → HTTPS
  - Segue redirecionamentos e verifica se o servidor está respondendo corretamente
  - Mensagens de status mais informativas indicando qual porta está respondendo
  - Melhor tratamento de casos onde apenas uma das portas está disponível

### 📝 Arquivos Modificados
- `multimax/routes/dbadmin.py`: 
  - Função `_check_nginx_health()` completamente refatorada
  - Adicionadas funções auxiliares `_test_port()` e `_check_http_redirect()`
  - Importações adicionadas: `urllib.request` e `urllib.error`

---

## [2.3] - 2025-01-XX

### 🎉 Novas Funcionalidades

#### Sistema de Arquivamento de Jornada
- **Arquivamento por Período**: Sistema completo para arquivar dados da jornada por período específico
  - Interface administrativa para selecionar período de arquivamento (data início e fim)
  - Copia todos os registros do período para tabela de arquivo permanente (`JornadaArchive`)
  - Remove registros originais após arquivamento, reiniciando contadores para novo período
  - Metadados de arquivamento (data de arquivamento, usuário que arquivou, descrição do período)
  - Acesso restrito a administradores e desenvolvedores
- **Histórico Completo**: Visualização de histórico completo de cada colaborador
  - Combina registros arquivados + registros atuais em uma única visualização
  - Disponível no perfil do colaborador através do botão "Ver Histórico Completo"
  - Abre em nova aba para facilitar navegação e comparação
  - Exibe totais consolidados (horas totais, folgas, conversões, valores pagos)
  - Indicação visual clara de registros arquivados vs. registros atuais
  - Tabela detalhada com todos os registros ordenados por data
- **Modelo de Dados**: Nova tabela `JornadaArchive` para armazenar registros arquivados
  - Mantém todos os dados originais (horas, dias, valores, observações, origin, etc.)
  - Preserva metadados originais (criado por, data de criação)
  - Índices otimizados para consultas rápidas por colaborador e período
  - Relacionamento com modelo `Collaborator` para consultas eficientes

#### Exportação de Produtos
- **Exclusão de Produtos**: Funcionalidade para excluir produtos do estoque
  - Botão de exclusão em cards do dashboard e tabela de produtos
  - Validação de permissões (apenas operador, admin e DEV)
  - Confirmação via JavaScript antes de excluir
  - Exclusão em cascata de registros históricos associados
  - Mensagens de feedback para o usuário

### 🐛 Correções

#### Gestão de Usuários e Colaboradores
- **Validação de Nome**: Adicionada validação obrigatória do nome ao criar colaborador/usuário
  - Prevenção de criação de usuários sem nome
  - Mensagens de erro claras para o usuário
- **Normalização de Username**: Username agora é normalizado automaticamente
  - Remove caracteres especiais e não alfanuméricos
  - Converte para minúsculas automaticamente
  - Mantém apenas letras e números
  - Validação para garantir que username normalizado não fique vazio após normalização
  - Mensagens de feedback exibem o username normalizado gerado
- **Melhorias de Segurança**: Validações adicionais para prevenir criação de usuários inválidos
  - Tratamento robusto de erros durante criação
  - Rollback automático em caso de falha

#### Sistema de Jornada
- **Cálculo de Saldo no Perfil**: Correção crítica no cálculo de horas e folgas no perfil do colaborador
  - Exclusão correta de folgas com `origin='horas'` do cálculo de `credits_sum` para evitar duplicação
  - Remoção de código de reconciliação automática desatualizado que causava inconsistências
  - Uso da mesma lógica corrigida do sistema de jornada principal (`_calculate_collaborator_balance`)
  - Cálculos agora são consistentes entre perfil e página de jornada

#### Notificações
- **URL de Notificações de Limpeza**: Correção na URL das notificações de limpeza
  - Removida barra final desnecessária (`/cronograma/` → `/cronograma`)
  - Links agora funcionam corretamente quando clicados nas notificações
  - Correção aplicada em `multimax/routes/api.py` e `multimax/routes/home.py`

### 📝 Arquivos Modificados

#### Novos Arquivos
- `multimax/models.py`: Adicionado modelo `JornadaArchive` (26 linhas)
- `templates/jornada/arquivar.html`: Interface de arquivamento (79 linhas)
- `templates/jornada/historico.html`: Visualização de histórico completo (189 linhas)
- `INSTALACAO_VPS.md`: Documentação de instalação em VPS (166 linhas)
- `create_deploy_zip.py`: Script para criar pacote de deploy (92 linhas)

#### Arquivos Alterados
- `multimax/routes/jornada.py`: 
  - Rotas de arquivamento (`/arquivar`) e histórico (`/historico/<collaborator_id>`)
  - Funções auxiliares para arquivamento e visualização
  - Refatorações diversas (860 linhas adicionadas, 689 removidas)
- `multimax/routes/usuarios.py`: 
  - Correções na criação de usuários (`gestao_colabs_criar`)
  - Correção no cálculo de perfil (`perfil`)
  - Validações e normalização (20 linhas adicionadas, 58 removidas)
- `multimax/routes/exportacao.py`: 
  - Novas rotas de exportação PDF de jornada (252 linhas adicionadas)
- `multimax/routes/estoque.py`: 
  - Rota de exclusão de produtos (`excluir_produto`)
  - Exclusão em cascata de histórico (14 linhas adicionadas, 4 removidas)
- `multimax/routes/api.py`: 
  - Correção na URL de notificações (1 linha modificada)
- `templates/jornada/index.html`: 
  - Botão de arquivamento adicionado (31 linhas adicionadas, 4 removidas)
- `templates/perfil.html`: 
  - Botão para visualizar histórico completo (11 linhas adicionadas)
- `templates/produtos.html`: 
  - Botão de exclusão em tabela (11 linhas adicionadas, 2 removidas)
- `templates/index.html`: 
  - Botão de exclusão em cards de produtos (8 linhas adicionadas)

### 🔧 Melhorias Técnicas

- **Validações Robustas**: Validações mais robustas em formulários de criação de usuários
- **Normalização de Dados**: Normalização consistente de dados de entrada (usernames)
- **Estrutura de Arquivamento**: Estrutura de arquivamento preparada para histórico de longo prazo
- **Interface Administrativa**: Interface administrativa intuitiva para operações de arquivamento
- **Integridade de Dados**: Exclusão em cascata mantém integridade referencial
- **Performance**: Índices adicionados no modelo `JornadaArchive` para consultas eficientes

### 📊 Estatísticas da Versão

- **14 arquivos modificados**
- **1.760 linhas adicionadas**
- **758 linhas removidas**
- **5 arquivos novos criados**
- **1 modelo de banco de dados novo**

---

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
