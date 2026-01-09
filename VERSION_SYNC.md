# Sincronização de Versão - MultiMax

Este documento lista TODOS os lugares onde a versão do projeto MultiMax deve ser atualizada quando houver uma nova versão.

## Arquivos que contêm a versão do projeto:

1. **CHANGELOG.md** (linha 3)
   - Formato: `## [X.Y.Z] - YYYY-MM-DD`
   - Exemplo: `## [2.3.5] - 2025-01-04`

2. **multimax/__init__.py** (linha 634)
   - Função `_get_version()` - fallback quando Git não está disponível
   - Formato: `return 'X.Y.Z'`
   - Exemplo: `return '2.3.5'`

3. **LEIA-ME.txt** (linhas 3 e 75)
   - Linha 3: `Versão X.Y.Z - Mês YYYY`
   - Linha 75: `PRINCIPAIS FUNCIONALIDADES DA VERSÃO X.Y.Z:`
   - Exemplo: `Versão 2.3.5 - Janeiro 2025`

## Checklist de atualização de versão:

Quando for solicitada a atualização da versão, verificar e atualizar:

- [ ] CHANGELOG.md - adicionar nova entrada no topo
- [ ] multimax/__init__.py - atualizar fallback na linha 634
- [ ] LEIA-ME.txt - atualizar linha 3 e linha 75
- [ ] VERSION_SYNC.md - atualizar versão atual
- [ ] **CRIAR TAG GIT**: `git tag -a vX.Y.Z -m "Versão X.Y.Z - Descrição"`
- [ ] **PUSH DA TAG**: `git push origin vX.Y.Z`

## Nota importante:

- `README.md` e `requirements.txt` contêm `Flask>=2.3.0` - isso é a versão da biblioteca Flask, NÃO a versão do projeto MultiMax. Não alterar.
- `docker-compose.yml` contém `version: '3.9'` - isso é a versão do formato do docker-compose, NÃO a versão do projeto. Não alterar.

## Versão atual: 2.3.30

## Processo de Release:

Após atualizar a versão em todos os arquivos e fazer commit:

1. Criar tag anotada: `git tag -a vX.Y.Z -m "Versão X.Y.Z - Descrição das mudanças"`
2. Fazer push da tag: `git push origin vX.Y.Z`
3. A tag aparecerá no GitHub e poderá ser usada para criar releases

**IMPORTANTE**: Sempre criar a tag com a mesma versão atualizada nos arquivos!

