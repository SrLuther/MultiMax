## [2.3.23] - 2025-01-15

### 🎨 Melhorias de Interface

#### Sistema de Jornada - Layout Moderno
- **Refatoração Completa das Subpáginas**: Todas as subpáginas de Jornada agora utilizam design system moderno e elegante
- **Design System Unificado**: Aplicação consistente de glassmorphism, gradientes e animações em todas as páginas
- **Subpáginas Atualizadas**: 
  - Fechado para Revisão: Layout moderno com cards de status e navegação elegante
  - Arquivados: Estatísticas visuais, filtros modernos e paginação estilizada
  - Novo Registro: Formulário moderno com campos estilizados e ícones
  - Editar Registro: Interface elegante com feedback visual de bloqueios
  - Arquivar: Seleção de meses com checkboxes estilizados e alertas modernos
- **Calendário Automático**: Estilos modernos aplicados ao calendário com classes atualizadas
- **Botões Adicionais**: Adicionados botões info e warning ao design system
- **Responsividade**: Melhorias na experiência mobile para todas as subpáginas

#### Correções Técnicas
- **Git Fetch**: Corrigido comando `git fetch --all` removendo argumento `origin` incompatível
- **Classes CSS**: Padronização de todas as classes para design system moderno

---

## [2.3.22] - 2025-01-15

### 🔧 Correções Críticas

#### Inicialização do Backend
- **Tratamento de Erros na Criação do App**: Adicionado logging e tratamento robusto de exceções na inicialização do Flask
- **Fallback na Importação de Modelos**: Sistema agora tenta importação alternativa se a importação individual falhar
- **Prevenção de 502 Bad Gateway**: Melhorias para garantir que o backend inicie mesmo com problemas menores
- **Logs Críticos**: Adicionados logs detalhados para diagnóstico de problemas de inicialização

#### Sistema de Banco de Dados
- **Múltiplos Níveis de Fallback**: Sistema tenta criar tabelas em múltiplos níveis se houver erros
- **Tratamento de Erros de Importação**: Erros de importação de modelos não impedem mais o backend de iniciar

---
## [2.3.21] - 2025-01-15

### 🔧 Correções

#### Sistema de Jornada
- **Correção do Filtro Jinja2**: Removido uso do filtro `date` inexistente no template `em_aberto.html`, substituído por atualização dinâmica via JavaScript
- **Criação Automática de Todas as Tabelas**: Sistema agora cria automaticamente TODAS as tabelas ausentes do banco de dados na inicialização
- **Importação Completa de Modelos**: Garantida importação explícita de todos os modelos para registro no SQLAlchemy metadata
- **Logs Informativos**: Adicionados logs detalhados sobre criação automática de tabelas

#### Banco de Dados - Git Update
- **Melhorias no Tratamento de Erros Git Fetch**: Adicionada verificação prévia de remotes configurados
- **Diagnóstico de Erros**: Mensagens de erro mais detalhadas com sugestões específicas para resolver problemas
- **Exibição de Sugestões no Frontend**: Interface melhorada para exibir sugestões e detalhes de erros do git fetch

---
## [2.3.20] - 2025-01-15

### 🔧 Correções

#### Sistema de Jornada
- **Correção de Erro na Página Em Aberto**: Adicionado tratamento robusto de erros e criação automática da tabela `month_status` quando não existe
- **Criação Automática de Tabelas**: Sistema agora cria automaticamente a tabela `month_status` se não existir no banco de dados
- **Tratamento de Erros**: Melhor tratamento de exceções na rota `/jornada/em-aberto` com fallbacks seguros

---

## [2.3.19] - 2025-01-15

### ✨ Novas Funcionalidades

#### Sistema de Controle de Jornada Mensal
- **Estados do Mês**: Implementado sistema completo de estados (EM ABERTO, FECHADO PARA REVISÃO, ARQUIVADO)
- **Controle de Permissões**: Sistema rígido de permissões baseado em perfil (DEV, ADMIN, OPERADOR) e estado do mês
- **Três Subpáginas**: Separação clara entre meses em aberto, fechados para revisão e arquivados
- **Calendário Automático**: Calendário gerado automaticamente baseado em dados da jornada com integração de feriados
- **Transições de Estado**: Rotas para fechar mês, confirmar pagamento e arquivar, reabrir (DEV apenas)

### 🔧 Melhorias

#### Otimizações de Performance
- **Redução de CPU**: Intervalo de atualização de métricas aumentado de 5s para 10s
- **Pausa Automática**: Atualizações pausam automaticamente quando a página não está visível
- **Otimização de Gráficos**: Melhorias na renderização de gráficos Chart.js

#### Banco de Dados
- **Verificação de Banco**: Removida verificação que bloqueava atualizações quando banco está fora da pasta raiz
- **Atualizações Git**: Sistema não bloqueia mais atualizações por não encontrar banco no caminho esperado

#### Alertas
- **Limpar Alertas**: Novo botão para limpar todos os alertas ativos no card "Alertas Ativos"
- **Rota de Limpeza**: Endpoint `/db/alerts/clear` para limpar alertas programaticamente

---

## [2.3.18] - 2025-01-06

### ✨ Novas Funcionalidades

#### Monitoramento de Atualizações Git - Opções Avançadas
- **Forçar Checagem**: Novo botão que força uma checagem completa do repositório remoto com fetch agressivo (`--all --prune --force`)
- **Reinstalar Atualização**: Novo botão que permite forçar atualização mesmo quando o sistema já está atualizado
- **Verificação Inteligente**: Sistema verifica se há atualização disponível antes de executar (a menos que seja forçado)
- **Mensagens Contextuais**: Mensagens específicas quando o sistema já está atualizado, sugerindo usar "Reinstalar Atualização"

### 🔧 Melhorias

#### Backend
- Rota `git_status` agora aceita parâmetro `force` para fetch mais agressivo
- Rota `git_update` agora aceita parâmetro `force` no JSON para ignorar verificação de atualização
- Timeout aumentado para 30 segundos em checagens forçadas
- Logs melhorados indicando se é atualização normal ou forçada

#### Frontend
- Tratamento de erro melhorado quando sistema já está atualizado
- Estilos CSS adicionados para botão de warning (Reinstalar)
- Modal atualizado para mostrar se é atualização forçada

### 📝 Arquivos Modificados
- `multimax/routes/dbadmin.py`: Adicionado suporte a parâmetro `force` nas rotas Git
- `templates/db.html`: Adicionados botões "Forçar Checagem" e "Reinstalar Atualização"

---

## [2.3.17] - 2025-01-06

### 🐛 Correções

#### Página Jornada - Geração de PDF por Período
- **Filtro de Período**: Corrigido problema onde a seleção de período (Data Início e Data Fim) não estava sendo aplicada na geração de PDF
- **Submissão Automática**: Campos de data agora submetem o formulário automaticamente ao serem alterados
- **Links Atualizados**: Links de PDF são atualizados automaticamente com os parâmetros de período selecionados
- **Funcionalidade Completa**: Agora é possível gerar PDFs filtrados por período selecionado nos filtros da página

### 📝 Arquivos Modificados
- `templates/jornada/index.html`: Adicionado `onchange="this.form.submit()"` nos campos de data para submissão automática

---

# Changelog — MultiMax

## [2.3.16] - 2025-01-05

### ✨ Novas Funcionalidades

#### Grade Semanal da Escala
- **Exibição de Status**: A grade semanal agora exibe automaticamente quando um colaborador está de Folga, Férias ou Atestado
- **Prioridade sobre Turno**: O status (Folga/Férias/Atestado) tem prioridade sobre o turno configurado na escala
- **Badges Visuais**: Cada tipo de status possui um badge visual distinto:
  - **Folga**: Badge cinza com gradiente
  - **Férias**: Badge azul com gradiente
  - **Atestado**: Badge laranja com gradiente
- **Verificação Automática**: O sistema verifica automaticamente folgas agendadas, períodos de férias e atestados médicos

### 📝 Arquivos Modificados
- `multimax/routes/colaboradores.py`: Lógica de verificação de status e criação de status_map
- `templates/escala.html`: Exibição de status na grade semanal e estilos CSS

---

## [2.3.15] - 2025-01-05

### 🐛 Correções

#### Modo Dark - Legibilidade
- **Score de Saúde**: Corrigida legibilidade de textos no modo dark
  - Parágrafos, listas e itens agora usam cor clara (#e5e7eb) no modo dark
  - Elementos `<strong>` usam cor azul clara (#93c5fd) para melhor contraste
  - Garante leitura adequada de todos os textos explicativos

### 📝 Arquivos Modificados
- `templates/db.html`: Estilos CSS para modo dark na seção Score de Saúde

---

## [2.3.14] - 2025-01-05

### ⚡ Performance

#### Otimização de Uso de CPU
- **Intervalos de Atualização Frontend**: Reduzidos intervalos de atualização automática na página Banco de Dados
  - `fetchMetrics`: 1s → 5s (redução de 80%)
  - `refreshHealthChecks`: 10s → 30s (redução de 66%)
  - `updateLogs`: 3s → 10s (redução de 70%)
  - `refreshGitStatus`: 30s → 60s (redução de 50%)
  - `refreshDashboard`: 60s → 120s (redução de 50%)
- **Scheduler de Notificações**: Intervalo de verificação otimizado de 15s para 60s (redução de 75%)
- **Impacto**: Redução significativa no número de requisições HTTP e processamento no servidor

### 📝 Arquivos Modificados
- `templates/db.html`: Intervalos de atualização otimizados
- `multimax/__init__.py`: Intervalo do scheduler de notificações otimizado

---

## [2.3.13] - 2025-01-05

### 🐛 Correções

#### Detecção de Atualizações Git
- **Timeout Aumentado**: Aumentado timeout do `git fetch` de 10 para 15 segundos para garantir que o fetch complete
- **Cache do Navegador**: Adicionado timestamp na URL e headers no-cache para evitar cache do navegador
- **Logs Detalhados**: Adicionados logs informativos sobre fetch, commits e comparação
- **Debug no Frontend**: Adicionado console.log para facilitar diagnóstico no navegador
- **Comparação de Commits**: Melhorada lógica de comparação com logs detalhados

### 📝 Arquivos Modificados
- `multimax/routes/dbadmin.py`: Melhorias na detecção de atualizações Git
- `templates/db.html`: Prevenção de cache e logs de debug

---

## [2.3.12] - 2025-01-05

### ✨ Novas Funcionalidades

#### Explicação do Score de Saúde
- **Dashboard Consolidado**: Adicionada explicação detalhada no rodapé do card sobre como o Score de Saúde é calculado
- **Componentes Explicados**: Lista completa dos componentes considerados (Banco de Dados, Backend, CPU, Memória, Disco)
- **Interpretação**: Guia de interpretação do score (100 = ideal, <70 = atenção necessária)

### 🐛 Correções

#### Funcionalidade de Atualização Git
- **Instalação do Git**: Adicionado Git ao Dockerfile para permitir execução de comandos Git dentro do container
- **Mapeamento de Volume**: Adicionado volume `/opt/multimax:/opt/multimax:ro` no docker-compose.yml para acesso ao repositório Git
- **Variável de Ambiente**: Definida `GIT_REPO_DIR=/opt/multimax` no docker-compose.yml
- **Logs Detalhados**: Melhorados logs para diagnóstico de problemas com repositório Git
- **Tratamento de Erros**: Melhorado tratamento de exceções com logs informativos

### 📝 Arquivos Modificados
- `templates/db.html`: Explicação do Score de Saúde
- `Dockerfile`: Instalação do Git
- `docker-compose.yml`: Volume do repositório Git e variável de ambiente
- `multimax/routes/dbadmin.py`: Logs detalhados e melhor tratamento de erros
- `multimax/__init__.py`: Versão atualizada
- `LEIA-ME.txt`: Versão atualizada
- `VERSION_SYNC.md`: Versão atualizada

---

## [2.3.11] - 2025-01-04

### 📝 Documentação

#### Processo de Atualização de Versão
- **Documento de Processo**: Criado `PROCESSO_ATUALIZACAO_VERSAO.md` com checklist obrigatório
  - Define regra crítica: sempre atualizar versão e criar tag ao fazer push
  - Inclui processo passo a passo completo
  - Adiciona convenção de versionamento
  - Fornece exemplos práticos de uso

### 📝 Arquivos Modificados
- `PROCESSO_ATUALIZACAO_VERSAO.md`: Novo documento com processo obrigatório

---

## [2.3.10] - 2025-01-04

### 🐛 Correções

#### Correções de Exibição
- **Card Git na Página Banco de Dados**: Corrigido problema de visibilidade do card de monitoramento Git
  - Adicionado CSS com `!important` para garantir que o card seja sempre visível
  - Card agora aparece corretamente para usuários DEV
- **Valores no Perfil do Usuário**: Corrigido cálculo e exibição de valores a receber
  - Reimplementado cálculo diretamente no perfil sem dependência de importação
  - Adicionado `AppSetting` aos imports necessários
  - Melhorada condição de exibição com mensagens informativas
  - Valores agora aparecem corretamente quando colaborador está vinculado

### 📝 Arquivos Modificados
- `multimax/routes/usuarios.py`: Reimplementado cálculo de valores no perfil
- `templates/perfil.html`: Melhorada exibição de valores com mensagens informativas
- `templates/db.html`: Corrigida visibilidade do card Git

---

## [2.3.9] - 2025-01-04

### ✨ Novas Funcionalidades

#### Monitoramento de Atualizações Git na Página Banco de Dados
- **Card de Monitoramento Git**: Adicionado card na página Banco de Dados para monitorar atualizações do repositório Git
  - Monitora automaticamente o branch `nova-versao-deploy` a cada 30 segundos
  - Exibe versão atual do sistema, commit atual e último commit remoto
  - Mostra mensagem do commit mais recente
  - Indica claramente se há atualização disponível
- **Botão "Aplicar Atualização"**:
  - Popup de confirmação com aviso sobre reinicialização do sistema
  - Contagem regressiva de 10 segundos antes de permitir confirmação
  - Executa comandos em sequência: `git fetch`, `git reset --hard`, `docker-compose down`, `docker-compose up -d`
  - Atualização automática do card após aplicar mudanças
- **Rotas Backend**:
  - `/db/git/status`: Retorna status do Git e commits
  - `/db/git/update`: Aplica atualização e reinicia containers Docker
- **Segurança**: Acesso restrito apenas para desenvolvedores (nível DEV)

#### Valores a Receber no Perfil do Usuário
- **Seção de Valores no Perfil**: Adicionada seção mostrando valores monetários a receber
  - Exibe 4 cards: Valor Dias Completos, Valor Horas Parciais, Valor Total Individual e Valor por Dia
  - Usa a mesma lógica de cálculo da página Jornada
  - Design harmonioso com gradiente verde
  - Link para ver detalhes na página Jornada
  - Alerta quando valor por dia não está configurado

---

## [2.3.8] - 2025-01-04

### ✨ Novas Funcionalidades

#### Visualizador de PDF na Jornada
- **Visualização de PDF no Navegador**: Adicionada página dedicada para visualizar PDFs de jornada diretamente no navegador
  - PDF exibido em iframe responsivo
  - Interface otimizada para dispositivos móveis
  - Suporte completo para visualização, download, compartilhar e imprimir
- **Controles de Ação**:
  - Botão de Download para salvar PDF localmente
  - Botão de Compartilhar com suporte a Web Share API (nativo em mobile)
  - Botão de Imprimir que abre diálogo de impressão do navegador
  - Botão Voltar para retornar à página Jornada
- **Otimização Mobile**:
  - Layout totalmente responsivo
  - Botões em coluna para melhor usabilidade em telas pequenas
  - Suporte a gestos e toques
  - Indicador de carregamento
- **Melhorias de UX**:
  - Links na página Jornada agora abrem visualizador ao invés de download direto
  - Fallback para copiar link quando Web Share API não está disponível
  - Tratamento de erros de carregamento

---

## [2.3.7] - 2025-01-04

### 🐛 Correções

#### Sistema de Valores na Jornada
- **Card Valor Dias + Horas (Individual)**: Corrigido cálculo e exibição do card
  - Agora mostra corretamente a soma de dias completos + horas parciais (value_total_individual)
  - Antes mostrava apenas o valor das horas parciais (value_residual_hours)
  - Detalhe atualizado para mostrar "X dia(s) + Yh proporcional" de forma mais clara
  - Todos os cards agora refletem os cálculos corretamente

---

## [2.3.6] - 2025-01-04

### 🔧 Correções

#### Docker Compose - Volume do Banco de Dados
- **Volume Persistente em Produção**: Corrigido volume do banco SQLite no docker-compose.yml
  - Volume atualizado para usar caminho absoluto `/opt/multimax/multimax-data:/app/data`
  - Garante persistência definitiva dos dados na VPS em produção
  - Container continua lendo o banco como `/app/data/estoque.db` internamente
  - Elimina dependência de caminhos relativos que podem variar

---

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


### ✨ Novas Funcionalidades

#### Grade Semanal da Escala
- **Exibição de Status**: A grade semanal agora exibe automaticamente quando um colaborador está de Folga, Férias ou Atestado
- **Prioridade sobre Turno**: O status (Folga/Férias/Atestado) tem prioridade sobre o turno configurado na escala
- **Badges Visuais**: Cada tipo de status possui um badge visual distinto:
  - **Folga**: Badge cinza com gradiente
  - **Férias**: Badge azul com gradiente
  - **Atestado**: Badge laranja com gradiente
- **Verificação Automática**: O sistema verifica automaticamente folgas agendadas, períodos de férias e atestados médicos

### 📝 Arquivos Modificados
- `multimax/routes/colaboradores.py`: Lógica de verificação de status e criação de status_map
- `templates/escala.html`: Exibição de status na grade semanal e estilos CSS

---

## [2.3.15] - 2025-01-05

### 🐛 Correções

#### Modo Dark - Legibilidade
- **Score de Saúde**: Corrigida legibilidade de textos no modo dark
  - Parágrafos, listas e itens agora usam cor clara (#e5e7eb) no modo dark
  - Elementos `<strong>` usam cor azul clara (#93c5fd) para melhor contraste
  - Garante leitura adequada de todos os textos explicativos

### 📝 Arquivos Modificados
- `templates/db.html`: Estilos CSS para modo dark na seção Score de Saúde

---

## [2.3.14] - 2025-01-05

### ⚡ Performance

#### Otimização de Uso de CPU
- **Intervalos de Atualização Frontend**: Reduzidos intervalos de atualização automática na página Banco de Dados
  - `fetchMetrics`: 1s → 5s (redução de 80%)
  - `refreshHealthChecks`: 10s → 30s (redução de 66%)
  - `updateLogs`: 3s → 10s (redução de 70%)
  - `refreshGitStatus`: 30s → 60s (redução de 50%)
  - `refreshDashboard`: 60s → 120s (redução de 50%)
- **Scheduler de Notificações**: Intervalo de verificação otimizado de 15s para 60s (redução de 75%)
- **Impacto**: Redução significativa no número de requisições HTTP e processamento no servidor

### 📝 Arquivos Modificados
- `templates/db.html`: Intervalos de atualização otimizados
- `multimax/__init__.py`: Intervalo do scheduler de notificações otimizado

---

## [2.3.13] - 2025-01-05

### 🐛 Correções

#### Detecção de Atualizações Git
- **Timeout Aumentado**: Aumentado timeout do `git fetch` de 10 para 15 segundos para garantir que o fetch complete
- **Cache do Navegador**: Adicionado timestamp na URL e headers no-cache para evitar cache do navegador
- **Logs Detalhados**: Adicionados logs informativos sobre fetch, commits e comparação
- **Debug no Frontend**: Adicionado console.log para facilitar diagnóstico no navegador
- **Comparação de Commits**: Melhorada lógica de comparação com logs detalhados

### 📝 Arquivos Modificados
- `multimax/routes/dbadmin.py`: Melhorias na detecção de atualizações Git
- `templates/db.html`: Prevenção de cache e logs de debug

---

## [2.3.12] - 2025-01-05

### ✨ Novas Funcionalidades

#### Explicação do Score de Saúde
- **Dashboard Consolidado**: Adicionada explicação detalhada no rodapé do card sobre como o Score de Saúde é calculado
- **Componentes Explicados**: Lista completa dos componentes considerados (Banco de Dados, Backend, CPU, Memória, Disco)
- **Interpretação**: Guia de interpretação do score (100 = ideal, <70 = atenção necessária)

### 🐛 Correções

#### Funcionalidade de Atualização Git
- **Instalação do Git**: Adicionado Git ao Dockerfile para permitir execução de comandos Git dentro do container
- **Mapeamento de Volume**: Adicionado volume `/opt/multimax:/opt/multimax:ro` no docker-compose.yml para acesso ao repositório Git
- **Variável de Ambiente**: Definida `GIT_REPO_DIR=/opt/multimax` no docker-compose.yml
- **Logs Detalhados**: Melhorados logs para diagnóstico de problemas com repositório Git
- **Tratamento de Erros**: Melhorado tratamento de exceções com logs informativos

### 📝 Arquivos Modificados
- `templates/db.html`: Explicação do Score de Saúde
- `Dockerfile`: Instalação do Git
- `docker-compose.yml`: Volume do repositório Git e variável de ambiente
- `multimax/routes/dbadmin.py`: Logs detalhados e melhor tratamento de erros
- `multimax/__init__.py`: Versão atualizada
- `LEIA-ME.txt`: Versão atualizada
- `VERSION_SYNC.md`: Versão atualizada

---

## [2.3.11] - 2025-01-04

### 📝 Documentação

#### Processo de Atualização de Versão
- **Documento de Processo**: Criado `PROCESSO_ATUALIZACAO_VERSAO.md` com checklist obrigatório
  - Define regra crítica: sempre atualizar versão e criar tag ao fazer push
  - Inclui processo passo a passo completo
  - Adiciona convenção de versionamento
  - Fornece exemplos práticos de uso

### 📝 Arquivos Modificados
- `PROCESSO_ATUALIZACAO_VERSAO.md`: Novo documento com processo obrigatório

---

## [2.3.10] - 2025-01-04

### 🐛 Correções

#### Correções de Exibição
- **Card Git na Página Banco de Dados**: Corrigido problema de visibilidade do card de monitoramento Git
  - Adicionado CSS com `!important` para garantir que o card seja sempre visível
  - Card agora aparece corretamente para usuários DEV
- **Valores no Perfil do Usuário**: Corrigido cálculo e exibição de valores a receber
  - Reimplementado cálculo diretamente no perfil sem dependência de importação
  - Adicionado `AppSetting` aos imports necessários
  - Melhorada condição de exibição com mensagens informativas
  - Valores agora aparecem corretamente quando colaborador está vinculado

### 📝 Arquivos Modificados
- `multimax/routes/usuarios.py`: Reimplementado cálculo de valores no perfil
- `templates/perfil.html`: Melhorada exibição de valores com mensagens informativas
- `templates/db.html`: Corrigida visibilidade do card Git

---

## [2.3.9] - 2025-01-04

### ✨ Novas Funcionalidades

#### Monitoramento de Atualizações Git na Página Banco de Dados
- **Card de Monitoramento Git**: Adicionado card na página Banco de Dados para monitorar atualizações do repositório Git
  - Monitora automaticamente o branch `nova-versao-deploy` a cada 30 segundos
  - Exibe versão atual do sistema, commit atual e último commit remoto
  - Mostra mensagem do commit mais recente
  - Indica claramente se há atualização disponível
- **Botão "Aplicar Atualização"**:
  - Popup de confirmação com aviso sobre reinicialização do sistema
  - Contagem regressiva de 10 segundos antes de permitir confirmação
  - Executa comandos em sequência: `git fetch`, `git reset --hard`, `docker-compose down`, `docker-compose up -d`
  - Atualização automática do card após aplicar mudanças
- **Rotas Backend**:
  - `/db/git/status`: Retorna status do Git e commits
  - `/db/git/update`: Aplica atualização e reinicia containers Docker
- **Segurança**: Acesso restrito apenas para desenvolvedores (nível DEV)

#### Valores a Receber no Perfil do Usuário
- **Seção de Valores no Perfil**: Adicionada seção mostrando valores monetários a receber
  - Exibe 4 cards: Valor Dias Completos, Valor Horas Parciais, Valor Total Individual e Valor por Dia
  - Usa a mesma lógica de cálculo da página Jornada
  - Design harmonioso com gradiente verde
  - Link para ver detalhes na página Jornada
  - Alerta quando valor por dia não está configurado

---

## [2.3.8] - 2025-01-04

### ✨ Novas Funcionalidades

#### Visualizador de PDF na Jornada
- **Visualização de PDF no Navegador**: Adicionada página dedicada para visualizar PDFs de jornada diretamente no navegador
  - PDF exibido em iframe responsivo
  - Interface otimizada para dispositivos móveis
  - Suporte completo para visualização, download, compartilhar e imprimir
- **Controles de Ação**:
  - Botão de Download para salvar PDF localmente
  - Botão de Compartilhar com suporte a Web Share API (nativo em mobile)
  - Botão de Imprimir que abre diálogo de impressão do navegador
  - Botão Voltar para retornar à página Jornada
- **Otimização Mobile**:
  - Layout totalmente responsivo
  - Botões em coluna para melhor usabilidade em telas pequenas
  - Suporte a gestos e toques
  - Indicador de carregamento
- **Melhorias de UX**:
  - Links na página Jornada agora abrem visualizador ao invés de download direto
  - Fallback para copiar link quando Web Share API não está disponível
  - Tratamento de erros de carregamento

---

## [2.3.7] - 2025-01-04

### 🐛 Correções

#### Sistema de Valores na Jornada
- **Card Valor Dias + Horas (Individual)**: Corrigido cálculo e exibição do card
  - Agora mostra corretamente a soma de dias completos + horas parciais (value_total_individual)
  - Antes mostrava apenas o valor das horas parciais (value_residual_hours)
  - Detalhe atualizado para mostrar "X dia(s) + Yh proporcional" de forma mais clara
  - Todos os cards agora refletem os cálculos corretamente

---

## [2.3.6] - 2025-01-04

### 🔧 Correções

#### Docker Compose - Volume do Banco de Dados
- **Volume Persistente em Produção**: Corrigido volume do banco SQLite no docker-compose.yml
  - Volume atualizado para usar caminho absoluto `/opt/multimax/multimax-data:/app/data`
  - Garante persistência definitiva dos dados na VPS em produção
  - Container continua lendo o banco como `/app/data/estoque.db` internamente
  - Elimina dependência de caminhos relativos que podem variar

---

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
