# Pre-Commit Hook: CHANGELOG Enforcement

## Visão Geral

Um hook de pre-commit automático foi implementado para garantir que toda mudança de código seja acompanhada de uma **NOVA VERSÃO** no arquivo `CHANGELOG.md`. 

**Regras Rigorosas:**
1. ✅ Exige criação de NOVA versão (nunca editar existentes)
2. ✅ Previne modificação de versões já lançadas
3. ✅ Valida formato semântico (MAJOR.MINOR.PATCH)
4. ✅ Mantém histórico imutável

## Como Funciona

### Instalação

O hook é instalado automaticamente quando você executa:

```bash
pre-commit install
```

Ele é ativado antes de cada commit Git e verifica se:

1. **Há arquivos de código modificados** (`.py`, `.html`, `.js`, `.css`, `.sql`, `.json`)
2. **Se houver mudanças de código**: Uma **NOVA VERSÃO** deve ser criada em `CHANGELOG.md`
3. **Versões já lançadas**: JAMAIS podem ser editadas ou removidas
4. **Formato de versão**: Deve seguir semver (X.Y.Z) ou estar em [Unreleased]

### Comportamento

#### ✅ Cenário Permitido - Commit com sucesso

```bash
# Modificou código E criou NOVA versão no CHANGELOG
git add src/models.py CHANGELOG.md
git commit -m "feat: new feature"
# ✓ Commit aceito!
```

**CHANGELOG.md atualizado corretamente:**
```markdown
## [Unreleased]

## [2.7.5] - 2026-01-21

### Funcionalidades

- feat(produtos): nova feature adicionada

## [2.7.4] - 2026-01-20
...versões anteriores...
```

#### ❌ Cenários Bloqueados

**Cenário 1: CHANGELOG não foi atualizado**
```bash
git add src/models.py
git commit -m "feat: new feature"

# ❌ BLOQUEADO: CHANGELOG.md não foi staged
```

**Cenário 2: Apenas editou [Unreleased] existente**
```bash
# Modificou CHANGELOG sem criar NOVA versão
git add src/models.py CHANGELOG.md
git commit -m "feat: new feature"

# ❌ BLOQUEADO: Nenhuma nova versão foi criada!
# ERRO: Code modified but NO NEW VERSION was created in CHANGELOG.md
```

**Cenário 3: Tentou editar versão lançada**
```bash
# Tentou editar versão 2.7.4 existente
git add CHANGELOG.md
git commit -m "fix: typo in old version"

# ❌ BLOQUEADO: Não é permitido modificar versões já lançadas!
# ERRO: Cannot remove or modify existing RELEASED versions!
```

## Formato Correto do CHANGELOG

**Sempre adicione NOVA versão NO TOPO:**

```markdown
## [Unreleased]

## [2.7.5] - 2026-01-21

### Funcionalidades

- feat(produtos): nova feature

### Correções

- fix(bug): descrição da correção

### Melhorias

- refactor(código): melhor design

## [2.7.4] - 2026-01-20
... versões anteriores (IMUTÁVEIS) ...
```

## Estrutura do Hook

### Arquivo Principal

**Localização:** `tools/check_changelog_updated.py`

Script Python que:
- Obtém lista de arquivos staged
- Verifica se há arquivos de código modificados
- Valida se **NOVA VERSÃO** foi criada (não apenas edições)
- Previne modificação de versões já lançadas
- Valida formato semântico (MAJOR.MINOR.PATCH)
- Retorna código 0 (sucesso) ou 1 (bloqueado)

**Validações realizadas:**

1. **Existência**: CHANGELOG.md deve estar staged
2. **Novas versões**: Pelo menos 1 versão nova deve ser adicionada
3. **Formato**: Versões devem ser X.Y.Z ou [Unreleased]
4. **Integridade**: Versões lançadas não podem ser removidas/editadas
5. **Semântica**: Versão anterior deve estar preservada

### Configuração

**Localização:** `.pre-commit-config.yaml`

```yaml
- repo: local
  hooks:
    - id: check-changelog-updated
      name: Check CHANGELOG Updated (Requires NEW Version)
      entry: python tools/check_changelog_updated.py
      language: system
      always_run: true
      pass_filenames: false
```

## Fluxo Correto ao Commitar

```bash
# 1. Faça suas mudanças de código
# 2. Edite o CHANGELOG.md:
#    - Mantenha [Unreleased] ou crie [X.Y.Z] novo
#    - NUNCA edite versões antigas
# 3. Stage ambos arquivos
git add src/models.py CHANGELOG.md

# 4. Commit (hook vai validar)
git commit -m "feat: description"
```

## Exceções

Commits que **não acionam** o hook:

1. **Apenas alterações de documentação pura** (README.md, etc)
2. **Apenas configuração** (.pre-commit-config.yaml, pyproject.toml)
3. **Sem arquivos staged** (repositório limpo)

## Bypass (Emergência Apenas)

Se absolutamente necessário contornar o hook:

```bash
git commit --no-verify -m "emergency: commit without changelog"
```

⚠️ **EVITE usar `--no-verify`!** Destrói a integridade do histórico.

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
