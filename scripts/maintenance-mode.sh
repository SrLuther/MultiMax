#!/bin/bash

# Script para ativar/desativar modo de manutenção do MultiMax
# Uso: ./maintenance-mode.sh [on|off|status]

set -e

ENV_FILE=".env.txt"
ENV_FILE_ALT=".env"

# Determina qual arquivo .env usar
if [ -f "$ENV_FILE" ]; then
    TARGET_FILE="$ENV_FILE"
elif [ -f "$ENV_FILE_ALT" ]; then
    TARGET_FILE="$ENV_FILE_ALT"
else
    echo "❌ Nenhum arquivo .env encontrado (.env.txt ou .env)"
    echo "💡 Criando $ENV_FILE..."
    touch "$ENV_FILE"
    TARGET_FILE="$ENV_FILE"
fi

# Função para obter status atual
get_status() {
    if grep -q "^MAINTENANCE_MODE=true" "$TARGET_FILE" 2>/dev/null; then
        echo "ON"
    elif grep -q "^MAINTENANCE_MODE=false" "$TARGET_FILE" 2>/dev/null; then
        echo "OFF"
    else
        echo "NOT_SET"
    fi
}

# Função para ativar modo de manutenção
enable_maintenance() {
    echo "🔧 Ativando modo de manutenção..."

    # Remove linha existente (se houver)
    if grep -q "^MAINTENANCE_MODE=" "$TARGET_FILE" 2>/dev/null; then
        # Usar sed compatível com Linux e macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' '/^MAINTENANCE_MODE=/d' "$TARGET_FILE"
        else
            sed -i '/^MAINTENANCE_MODE=/d' "$TARGET_FILE"
        fi
    fi

    # Adiciona configuração
    echo "MAINTENANCE_MODE=true" >> "$TARGET_FILE"

    echo "✅ Modo de manutenção ATIVADO em $TARGET_FILE"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Reinicie a aplicação:"
    echo "      • python app.py"
    echo "      • docker-compose restart (se usando Docker)"
    echo ""
    echo "   2. Verifique o status:"
    echo "      curl -I https://multimax.tec.br"
    echo "      (deve retornar HTTP 503)"
    echo ""
    echo "   3. Para desativar, execute:"
    echo "      ./maintenance-mode.sh off"
}

# Função para desativar modo de manutenção
disable_maintenance() {
    echo "🔓 Desativando modo de manutenção..."

    # Remove linha existente (se houver)
    if grep -q "^MAINTENANCE_MODE=" "$TARGET_FILE" 2>/dev/null; then
        # Usar sed compatível com Linux e macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' '/^MAINTENANCE_MODE=/d' "$TARGET_FILE"
        else
            sed -i '/^MAINTENANCE_MODE=/d' "$TARGET_FILE"
        fi
    fi

    # Adiciona configuração
    echo "MAINTENANCE_MODE=false" >> "$TARGET_FILE"

    echo "✅ Modo de manutenção DESATIVADO em $TARGET_FILE"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Reinicie a aplicação:"
    echo "      • python app.py"
    echo "      • docker-compose restart (se usando Docker)"
    echo ""
    echo "   2. Verifique o acesso:"
    echo "      https://multimax.tec.br"
}

# Função para mostrar status
show_status() {
    STATUS=$(get_status)

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  STATUS DO MODO DE MANUTENÇÃO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Arquivo: $TARGET_FILE"
    echo ""

    case $STATUS in
        "ON")
            echo "🔧 Status: ATIVADO"
            echo "⚠️  Sistema está em modo de manutenção"
            echo "📄 Usuários veem: página estática institucional"
            echo "🚫 Acesso bloqueado: todas as rotas, APIs e banco de dados"
            ;;
        "OFF")
            echo "✅ Status: DESATIVADO"
            echo "🟢 Sistema está operacional"
            echo "📄 Usuários veem: sistema completo"
            ;;
        "NOT_SET")
            echo "⚪ Status: NÃO CONFIGURADO"
            echo "ℹ️  Variável MAINTENANCE_MODE não definida"
            echo "📝 Sistema funciona normalmente (padrão: desativado)"
            ;;
    esac

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Menu principal
case "${1:-}" in
    on|enable|ativar)
        enable_maintenance
        ;;
    off|disable|desativar)
        disable_maintenance
        ;;
    status|check)
        show_status
        ;;
    *)
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Gerenciador de Modo de Manutenção"
        echo "  Sistema MultiMax"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Uso: $0 [comando]"
        echo ""
        echo "Comandos disponíveis:"
        echo "  on, enable, ativar     Ativa modo de manutenção"
        echo "  off, disable, desativar  Desativa modo de manutenção"
        echo "  status, check          Mostra status atual"
        echo ""
        echo "Exemplos:"
        echo "  $0 on      # Ativar"
        echo "  $0 off     # Desativar"
        echo "  $0 status  # Ver status"
        echo ""
        show_status
        ;;
esac
