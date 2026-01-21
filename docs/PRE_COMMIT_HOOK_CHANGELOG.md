# Pre-Commit Hook: CHANGELOG Enforcement

## Visão Geral

Um hook de pre-commit automático foi implementado para garantir que toda mudança de código seja acompanhada de uma atualização no arquivo `CHANGELOG.md`. Isso previne commits esquecidos e mantém o histórico de mudanças sempre sincronizado com o código.

## Como Funciona

### Instalação

O hook é instalado automaticamente quando você executa:

```bash
pre-commit install
```

Ele é ativado antes de cada commit Git e verifica se:

1. **Há arquivos de código modificados** (`.py`, `.html`, `.js`, `.css`, `.sql`, `.json`)
2. **Se houver mudanças de código**: O arquivo `CHANGELOG.md` DEVE estar também modificado (staged)
3. **Se apenas documentação foi modificada**: O commit é permitido sem atualizar CHANGELOG

### Comportamento

#### ✅ Cenário Permitido - Commit com sucesso

```bash
# Modificou código E atualizou CHANGELOG
git add src/models.py CHANGELOG.md
git commit -m "feat: new feature"
# ✓ Commit aceito!
```

#### ❌ Cenário Bloqueado - Commit recusado

```bash
# Modificou código MAS NÃO atualizou CHANGELOG
git add src/models.py
git commit -m "feat: new feature"

# Output:
# ======================================================================
# [ERROR] Code modified but CHANGELOG.md was not updated
# ======================================================================
#
# Modified files (staged):
#    * src/models.py
#
# Please:
#    1. Open CHANGELOG.md
#    2. Add entry in [Unreleased] or create new version section
#    3. Run: git add CHANGELOG.md
#    4. Run commit again: git commit
# ======================================================================
```

## Formato do CHANGELOG

Sempre mantenha o CHANGELOG atualizado no topo com um novo versionamento ou seção `[Unreleased]`:

```markdown
## [2.7.4] - 2026-01-21

### Funcionalidades

- feat(produtos): descrição da nova feature

### Correções

- fix(bug): descrição da correção

### Melhorias

- refactor(código): descrição da melhoria
```

## Estrutura do Hook

### Arquivo Principal

**Localização:** `tools/check_changelog_updated.py`

Script Python que:
- Obtém lista de arquivos staged via `git diff --cached`
- Verifica se há arquivos de código modificados
- Valida se CHANGELOG.md foi incluído
- Retorna código 0 (sucesso) ou 1 (bloqueado)
- Usa ASCII-safe characters para compatibilidade cross-platform

### Configuração

**Localização:** `.pre-commit-config.yaml`

```yaml
- repo: local
  hooks:
    - id: check-changelog-updated
      name: Check CHANGELOG Updated
      entry: python tools/check_changelog_updated.py
      language: system
      always_run: true
      pass_filenames: false
```

## Exceções

Commits que **não acionam** o hook:

1. **Apenas alterações de documentação pura** (README.md, etc)
2. **Apenas configuração** (.pre-commit-config.yaml, pyproject.toml)
3. **Sem arquivos staged** (repositório limpo)

## Bypass (Emergência)

Se absolutamente necessário contornar o hook:

```bash
git commit --no-verify -m "emergency: commit without changelog"
```

⚠️ **Evite usar `--no-verify` regularmente!** Quebra o objetivo do automação.

## Troubleshooting

### O hook não está instalado

```bash
pre-commit install
```

### O hook não está funcionando

Verifique se o Python está disponível:

```bash
python --version
python tools/check_changelog_updated.py
```

### Erro de encoding

O script foi otimizado para usar apenas ASCII. Se receber erro de encoding:

1. Reinstale o hook:
   ```bash
   pre-commit install
   ```

2. Limpe cache:
   ```bash
   pre-commit clean
   pre-commit install
   ```

## Benefícios

✅ Documentação sempre sincronizada com código  
✅ Histórico de mudanças completo e confiável  
✅ Padrão de commit mais disciplinado  
✅ Facilita code reviews e auditorias  
✅ Zero configuração adicional necessária  

## Histórico

- **2026-01-20**: Hook implementado e testado com sucesso
  - Script criado: `tools/check_changelog_updated.py`
  - Configuração adicionada: `.pre-commit-config.yaml`
  - Compatibilidade Windows + Linux/Mac garantida
