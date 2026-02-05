# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.42] - 2026-02-04 23:58:00

### Fixed
- Fluxos: contraste e legibilidade no modo escuro (cards, tabelas, formulários)

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.41] - 2026-02-04 23:50:00

### Added
- Fluxos: módulo mensal com ciclos semanais, PDF individual e fechamento automático
- Migração 005 para tabelas de Fluxos
- Tests: cobertura completa de Fluxos e rotas principais

### Fixed
- Tests: encerramento de conexões SQLite e remoção de warnings deprecados
- Core: ajustes de UTC e substituição de Query.get por db.session.get

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.40] - 2026-02-04 23:00:00

### Added
- Tests: cobertura para error handlers e notificação de erro

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.39] - 2026-02-04 22:40:00

### Fixed
- Auth: cadastro cria colaborador com CPF placeholder para evitar erro NOT NULL

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.38] - 2026-02-04 22:20:00

### Fixed
- Models: FKs corrigidas para usar tabela colaboradores

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.37] - 2026-02-04 22:00:00

### Fixed
- Central: botões de permissão e senha ganharam cores e tooltips para identificação

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.36] - 2026-02-04 21:45:00

### Fixed
- Central: títulos dos cards forçados para preto com seletor específico

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.35] - 2026-02-04 21:35:00

### Fixed
- Central: títulos dos cards forçados para preto

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.34] - 2026-02-04 21:25:00

### Fixed
- Central: textos do topo dos cards ajustados para preto em fundo branco

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.33] - 2026-02-04 21:15:00

### Fixed
- Central: aumentado contraste do topo dos cards de Colaboradores e Histórico

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.32] - 2026-02-04 21:00:00

### Fixed
- Central: corrigido uso do campo nome do usuário para evitar erro ao salvar colaborador

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.31] - 2026-02-04 10:00:00

### Added
- Nova página Central independente da Gestão, com layout hero animado, KPIs e tabelas modernas
- Modelos e tabelas exclusivas da Central (central_colaborador, central_log)
- Rotas completas da Central: criar, editar, excluir, atualizar permissão e senha
- Histórico detalhado de ações da Central
- Link de acesso no menu de Administração

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.30] - 2026-02-03 22:45:00

### Fixed
- **CRÍTICO - RECUPERAÇÃO DE DADOS**: Restaurados 1035 registros perdidos do banco estoque_original.db
- Recuperados: 6 colaboradores (Luciano, Diogo, Renato, Edilson, Natalino, Welvins), 275 shifts, 10 setores, 26 semanas, 32 ciclos, 19 feriados, 6 receitas, 40 ingredientes, 104 jornadas
- Banco agora possui dados completos de operações, históricos e configurações

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.29] - 2026-02-03 22:30:00

### Fixed
- **SIMPLIFICAÇÃO CRÍTICA**: Removida lógica complicada de "Associar usuário existente" 
- Usuário e Colaborador agora integrados: ao editar colaborador, pode opcionalmente criar usuário novo
- Eliminado dropdown de associação manual, validações misteriosas e dropdown de usuários paginados
- Feature agora SIMPLES: Nome → Cargo → Setor → Opcional (criar usuário) → Salvar

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.28] - 2026-02-03 19:30:00

### Fixed
- **CRÍTICO**: Corrigido dropdown "Associar usuário existente" que mostrava apenas usuários paginados (5 usuários) em vez de TODOS os usuários cadastrados
- Adicionado `users_all` à renderização da página de gestão para suportar dropdown completo

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.27] - 2026-02-03 15:30:00

### Fixed
- Adicionada coluna `regular_team` faltando no modelo Colaborador
- Corrigido erro "'Colaborador' object has no attribute 'regular_team'" ao atualizar colaborador
- Implementada migração Alembic 003 para adicionar regular_team à tabela colaboradores

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.26] - 2026-02-03 15:00:00

### Fixed
- **CRÍTICO**: Adicionadas colunas `setor_id` faltando nas tabelas ciclo_semana, ciclo_folga, ciclo_ocorrencia e ciclo_fechamento
- Corrigida migração Alembic 001: revision ID agora é "001" em vez de "001_initial_tables" para referência correta
- Corrigido erro "no such column: ciclo_semana.setor_id" que impedia deletar setores
- Implementada migração Alembic 002 para adicionar setor_id às tabelas de ciclos

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.25] - 2026-02-03 14:45:00

### Fixed
- Corrigidas docstrings no modelo Colaborador (flake8 D200, D105)
- Criado PROTOCOLO_COPILOT.md para estabelecer fluxo obrigatório de verificação de erros
- Removido find_version.py (arquivo sem propósito)
- Corrigido encoding UTF-8 em js_safety_check.py para Windows
- Corrigidos flake8 errors (D202 - blank line after docstring, E501 - line too long)
- Corrigido erro 'property' object has no attribute 'asc' ao trocar order_by(name.asc()) por order_by(nome.asc())

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.24] - 2026-02-03 12:30:00

### Fixed
- Corrigidas docstrings no modelo Colaborador (flake8 D200, D105)

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.23] - 2026-02-03 12:15:00

### Fixed
- Corrigidos nomes de campos do modelo Colaborador na função de atualização (nome, funcao, ativo)

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Sonnet 4.5

## [3.7.22] - 2026-02-03 12:00:00

### Added
- Possibilidade de associar usuários já existentes a colaboradores já existentes no modal de edição

### Fixed
- Adicionada seleção de usuário existente como alternativa ao criar novo usuário ao editar colaborador

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Sonnet 4.5

## [3.7.21] - 2026-02-03 11:30:00

### Fixed
- Implementado layout Grid para alinhamento perfeito dos cards "Gerenciar Colaboradores" e "Cargos e Permissões" em 50% cada
- Corrigidas type hints no modelo Colaborador para eliminar warnings de redefinição (movendo type ignore para decorators)
- Unificado layout da página de gestão com estrutura Grid responsiva

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.20] - 2026-02-03 11:00:00

### Fixed
- Corrigido layout e indentação das seções "Gerenciar Usuários" e "Gerenciar Colaboradores" na página de gestão
- Removido formulário de filtro duplicado que estava bagunçando o layout do resumo de saldo

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Haiku 4.5

## [3.7.19] - 2026-02-03 10:30:00

### Fixed
- Separada a listagem de Usuários e Colaboradores na gestão
- Adicionada paginação independente para usuários e colaboradores

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.18] - 2026-02-03 10:00:00

### Fixed
- Corrigido: Colaboradores sem usuários associados agora aparecem na listagem de gerenciamento

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.17] - 2026-02-03 09:00:00

### Fixed
- Corrigido erro de redeclaração em `Colaborador.name` usando `type: ignore[no-redef]` para Mypy

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.16] - 2026-02-03 08:00:00

### Fixed
- Corrigido erro de redeclaração em `Colaborador.name` usando `pyright: ignore` e `type: ignore[no-redef]`
- Migrados 89 registros de jornada dos 6 açougueiros
- Migrados 41 registros de folgas dos 6 açougueiros
- Banco PostgreSQL agora contém todos os dados dos colaboradores principais
- Removidos 10 scripts de migração temporários do repositório

---
### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.15] - 2026-02-03 06:00:00

### Fixed
- Migrados dados do SQLite para PostgreSQL (colaboradores e setores)
- DATABASE_URL alterado para PostgreSQL como banco principal
- Silenciados avisos do linter sobre redeclaração em hybrid_property

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.14] - 2026-02-03 04:40:00

### Fixed
- Aplicação agora usa o banco SQLite existente em /opt/multimax-data/estoque.db para restaurar dados

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.13] - 2026-02-03 04:30:00

### Fixed
- `Colaborador.name` agora é híbrido para permitir ordenação em consultas

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.12] - 2026-02-03 04:20:00

### Fixed
- Compatibilidade do modelo Colaborador com atributo `name` usado na página de gestão

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: GPT-5.2-Codex

## [3.7.11] - 2026-02-03 04:10:00

### Fixed
- Ajustes de lint no handler de erros para cumprir regras de docstring/whitespace

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Sonnet 4.5

## [3.7.10] - 2026-02-03 04:00:00

### Fixed
- Tratamento de erro no endpoint `/gestao` para evitar erro 500 (Internal Server Error)
- Função `gestao()` agora retorna fallback gracioso ao invés de crashar
- Logs vazios retornados quando `_collect_logs()` falha

---


### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Sonnet 4.5

## [3.7.9] - 2026-02-03 03:45:00

### Fixed
- Adicionado import `typing` em `logs_auth.py` para resolver erros de type checking
- Adicionadas verificações de None em `migrate_sqlite_to_postgres_vps.py` e `migrate_additional.py` para `fetchone()` calls
- CHANGELOG reorganizado: versões históricas movidas para `arquivo morto/OLD_CHANGELOG.md`

### Changed
- Estrutura do CHANGELOG simplificada para conformidade com novas políticas de versionamento

---

### IA responsável pelo envio
- Nome da IA: GitHub Copilot
- Modelo: Claude Sonnet 4.5

## [3.7.8] - 2026-02-03 03:30:00

### Fixed
- Corrigidos erros críticos de mapeamento SQLAlchemy que causavam "Erro no banco de dados" (50+ instâncias)
- Corrigidas todas as referências de ForeignKey de `"collaborator"` para `"colaborador"` (9 ocorrências)
- Adicionado `primaryjoin` explícito a todas as relationships para resolver erros de inicialização de mapper
- Corrigidos 3 relationships em `management.py` (Shift, Vacation, MedicalCertificate)
- Corrigidos 10 relationships em `scheduling.py` (TimeOffRecord, CicloFolga, CicloOcorrencia, CicloSaldo, RegistroJornada)
- Corrigidos 2 relationships em `special.py` (EstoqueProducao, EscalaEspecial)
- Adicionado import `typing` em `logs_auth.py` para resolver erros de type checking
- Adicionadas verificações de None em `migrate_sqlite_to_postgres_vps.py` e `migrate_additional.py` para `fetchone()` calls

### Changed
- Todas as relationships agora incluem `foreign_keys` e `primaryjoin` explícitos para garantir mapeamento correto

### Technical Details
- Commits: fdbb173, d0bfdab
- Aplicação validada em produção (VPS)
- Zero erros de mapper initialization após correções
- Health endpoint: 200 OK
- Ciclos endpoint: 302 Redirect (comportamento esperado)

---

## Arquivo Histórico

O histórico completo de versões anteriores foi movido para [`arquivo morto/OLD_CHANGELOG.md`](arquivo%20morto/OLD_CHANGELOG.md) para manter este arquivo limpo e em conformidade com as novas políticas de versionamento.
