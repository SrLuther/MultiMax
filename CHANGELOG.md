# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
