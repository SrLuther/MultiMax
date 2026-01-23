#!/bin/bash
# MultiMax - Reiniciar Aplicação
# Uso: sudo systemctl restart multimax
# ou: ./scripts/app-restart.sh

set -euo pipefail

SERVICE_NAME="multimax"

echo "🔄 Reiniciando $SERVICE_NAME..."
if systemctl restart "$SERVICE_NAME"; then
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ $SERVICE_NAME reiniciado com sucesso"
        systemctl status "$SERVICE_NAME"
    else
        echo "❌ Falha ao reiniciar $SERVICE_NAME"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
else
    echo "❌ Erro ao reiniciar $SERVICE_NAME"
    exit 1
fi
