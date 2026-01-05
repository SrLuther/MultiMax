# Processo de Atualização de Versão - MultiMax

## ⚠️ REGRA CRÍTICA

**SEMPRE que houver push para o GitHub, a versão DEVE ser atualizada e uma tag DEVE ser criada!**

## Checklist Obrigatório

Antes de fazer qualquer push para o GitHub, verificar:

- [ ] Versão atualizada em `CHANGELOG.md`
- [ ] Versão atualizada em `multimax/__init__.py` (linha ~641)
- [ ] Versão atualizada em `LEIA-ME.txt` (linhas 3 e 75)
- [ ] Versão atualizada em `VERSION_SYNC.md`
- [ ] **Tag Git criada**: `git tag -a vX.Y.Z -m "Versão X.Y.Z - Descrição"`
- [ ] **Tag enviada**: `git push origin vX.Y.Z`
- [ ] Commit e push do código: `git push origin nova-versao-deploy`

## Processo Passo a Passo

### 1. Atualizar Versão nos Arquivos

```bash
# Opção 1: Usar script automatizado
python update_version.py 2.3.X "Descrição das mudanças"

# Opção 2: Atualizar manualmente
# Editar CHANGELOG.md, multimax/__init__.py, LEIA-ME.txt, VERSION_SYNC.md
```

### 2. Fazer Commit das Alterações

```bash
git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md
git commit -m "chore: Atualiza versão para X.Y.Z"
```

### 3. Criar Tag Git

```bash
git tag -a vX.Y.Z -m "Versão X.Y.Z - Descrição das mudanças"
```

### 4. Fazer Push

```bash
# Push do código
git push origin nova-versao-deploy

# Push da tag (IMPORTANTE!)
git push origin vX.Y.Z
```

## Convenção de Versionamento

- **MAJOR (X.0.0)**: Mudanças incompatíveis com versões anteriores
- **MINOR (0.X.0)**: Novas funcionalidades compatíveis com versões anteriores
- **PATCH (0.0.X)**: Correções de bugs e pequenas melhorias

## Lembrete Automático

O script `update_version.py` pode ser usado para automatizar a atualização:

```bash
python update_version.py 2.3.11 "Descrição"
```

O script atualiza todos os arquivos automaticamente, mas **ainda é necessário**:
1. Revisar as mudanças
2. Fazer commit
3. Criar tag
4. Fazer push

## Verificação Pós-Push

Após fazer push, verificar no GitHub:
- [ ] Tag aparece na lista de tags: `https://github.com/SrLuther/MultiMax/tags`
- [ ] Versão no CHANGELOG.md corresponde à tag
- [ ] Versão no código corresponde à tag

## Exemplo Completo

```bash
# 1. Atualizar versão
python update_version.py 2.3.11 "Correção de bug crítico"

# 2. Revisar mudanças
git diff

# 3. Adicionar e commitar
git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md
git commit -m "chore: Atualiza versão para 2.3.11"

# 4. Criar tag
git tag -a v2.3.11 -m "Versão 2.3.11 - Correção de bug crítico"

# 5. Push código
git push origin nova-versao-deploy

# 6. Push tag
git push origin v2.3.11
```

## ⚠️ NUNCA ESQUECER

- **Versão SEM tag = ERRO CRÍTICO**
- **Push SEM atualizar versão = ERRO CRÍTICO**
- **Tag SEM push = ERRO CRÍTICO**

Sempre seguir este processo completo!

