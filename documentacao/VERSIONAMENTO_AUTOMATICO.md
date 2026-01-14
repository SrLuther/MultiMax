# Versionamento Automático do MultiMax

## 📋 Visão Geral

O projeto MultiMax agora possui um sistema de versionamento automático que garante que **toda vez que você fizer push para o GitHub, a versão será automaticamente incrementada**.

## 🚀 Como Usar

### Opção 1: Script PowerShell (Windows - Recomendado)

```powershell
.\git-push-with-version.ps1 [branch] [tipo]
```

**Exemplos:**
```powershell
# Incrementa patch (2.6.0 -> 2.6.1) e faz push para nova-versao-deploy
.\git-push-with-version.ps1

# Incrementa minor (2.6.0 -> 2.7.0) e faz push para main
.\git-push-with-version.ps1 main minor

# Incrementa major (2.6.0 -> 3.0.0) e faz push para develop
.\git-push-with-version.ps1 develop major
```

### Opção 2: Script Bash (Linux/Mac)

```bash
./git-push-with-version.sh [branch] [tipo]
```

**Exemplos:**
```bash
# Incrementa patch (2.6.0 -> 2.6.1) e faz push para nova-versao-deploy
./git-push-with-version.sh

# Incrementa minor (2.6.0 -> 2.7.0) e faz push para main
./git-push-with-version.sh main minor

# Incrementa major (2.6.0 -> 3.0.0) e faz push para develop
./git-push-with-version.sh develop major
```

### Opção 3: Script Python (Manual)

Se você quiser apenas atualizar a versão sem fazer push:

```bash
python auto_version_update.py [patch|minor|major]
```

Depois faça o commit e push manualmente:
```bash
git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md
git commit -m "chore: Atualiza versao para X.Y.Z"
git tag -a vX.Y.Z -m "Versao X.Y.Z"
git push origin nova-versao-deploy
git push origin vX.Y.Z
```

## 📦 Tipos de Incremento

- **patch** (padrão): Incrementa o último número (2.6.0 -> 2.6.1)
  - Use para: correções de bugs, pequenas melhorias
- **minor**: Incrementa o número do meio (2.6.0 -> 2.7.0)
  - Use para: novas funcionalidades, melhorias significativas
- **major**: Incrementa o primeiro número (2.6.0 -> 3.0.0)
  - Use para: mudanças que quebram compatibilidade, refatorações grandes

## 📝 Arquivos Atualizados Automaticamente

O sistema atualiza automaticamente os seguintes arquivos:

1. **CHANGELOG.md**: Adiciona nova entrada no topo com a nova versão
2. **multimax/__init__.py**: Atualiza a versão no código
3. **LEIA-ME.txt**: Atualiza referências à versão
4. **VERSION_SYNC.md**: Atualiza a versão atual (se existir)

## 🔄 Fluxo Automático

Quando você usa `git-push-with-version.ps1` ou `git-push-with-version.sh`:

1. ✅ Detecta a versão atual
2. ✅ Incrementa a versão (patch por padrão)
3. ✅ Atualiza todos os arquivos de versão
4. ✅ Cria commit de versão automaticamente
5. ✅ Cria tag Git automaticamente
6. ✅ Faz push do branch
7. ✅ Faz push das tags

## ⚠️ Importante

- **SEMPRE use os scripts de push com versão** em vez de `git push` direto
- O sistema garante que **nunca haverá um push sem atualização de versão**
- Se você esquecer e usar `git push` direto, execute `python auto_version_update.py patch` antes

## 🛠️ Configuração

### Windows (PowerShell)

Para facilitar, você pode criar um alias no seu perfil PowerShell:

```powershell
# Adicione ao seu perfil PowerShell ($PROFILE)
function gpv { .\git-push-with-version.ps1 $args }
Set-Alias -Name gpush -Value gpv
```

Depois você pode usar simplesmente:
```powershell
gpush
```

### Linux/Mac (Bash)

Adicione ao seu `~/.bashrc` ou `~/.zshrc`:

```bash
alias gpush='./git-push-with-version.sh'
```

Depois você pode usar:
```bash
gpush
```

## 📚 Estrutura de Versão

O projeto segue o padrão [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (ex: 2.6.1)
- **MAJOR**: Mudanças incompatíveis
- **MINOR**: Funcionalidades compatíveis
- **PATCH**: Correções compatíveis

## 🔍 Verificar Versão Atual

Para verificar a versão atual:

```bash
python -c "import re; content = open('CHANGELOG.md').read(); match = re.search(r'^## \[(\d+\.\d+\.\d+)\]', content, re.MULTILINE); print(match.group(1) if match else 'Nao encontrado')"
```

Ou simplesmente abra o `CHANGELOG.md` e veja a primeira linha.

## 🐛 Solução de Problemas

### Erro: "Não foi possível determinar a versão atual"
- Verifique se o `CHANGELOG.md` existe e tem uma entrada de versão válida
- Verifique se `multimax/__init__.py` existe

### Erro: "Tag já existe"
- Isso é normal se você já criou a tag antes
- O script pula a criação de tag se ela já existir

### Erro de encoding no Windows
- O script foi configurado para evitar emojis e usar apenas ASCII
- Se ainda houver problemas, verifique a codificação do terminal

## 📞 Suporte

Se encontrar problemas, verifique:
1. Se o Python está instalado e no PATH
2. Se o Git está instalado e configurado
3. Se você está no diretório raiz do projeto
4. Se os arquivos de versão existem
