#!/bin/bash
# Script bash para fazer push com atualização automática de versão
# Uso: ./git-push-with-version.sh [branch] [patch|minor|major]

BRANCH="${1:-nova-versao-deploy}"
BUMP_TYPE="${2:-patch}"

echo "🚀 Atualizando versão antes do push..."

# Executa o script de atualização de versão
python3 auto_version_update.py "$BUMP_TYPE"

if [ $? -ne 0 ]; then
    echo "❌ Falha ao atualizar versão. Push cancelado."
    exit 1
fi

# Adiciona arquivos de versão ao staging
echo "📝 Adicionando arquivos de versão..."
git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md 2>/dev/null

# Verifica se há mudanças para commitar
if ! git diff --cached --quiet; then
    # Há mudanças, cria commit de versão
    CURRENT_VERSION=$(python3 -c "import re; content = open('CHANGELOG.md').read(); match = re.search(r'^## \[(\d+\.\d+\.\d+)\]', content, re.MULTILINE); print(match.group(1) if match else '')")
    if [ -n "$CURRENT_VERSION" ]; then
        echo "📦 Criando commit de versão $CURRENT_VERSION..."
        git commit -m "chore: Atualiza versão para $CURRENT_VERSION" --no-verify

        # Cria tag se não existir
        if ! git tag -l "v$CURRENT_VERSION" | grep -q "v$CURRENT_VERSION"; then
            echo "🏷️  Criando tag v$CURRENT_VERSION..."
            git tag -a "v$CURRENT_VERSION" -m "Versão $CURRENT_VERSION"
        fi
    fi
fi

# Faz push do branch
echo "⬆️  Fazendo push para $BRANCH..."
git push origin "$BRANCH"

if [ $? -eq 0 ]; then
    # Faz push das tags
    echo "🏷️  Fazendo push das tags..."
    git push origin --tags

    echo "✅ Push concluído com sucesso!"
else
    echo "❌ Erro ao fazer push."
    exit 1
fi
