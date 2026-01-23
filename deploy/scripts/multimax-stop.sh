#!/bin/bash
# MultiMax - Parar Aplicação
# Uso: sudo systemctl stop multimax
# ou: ./scripts/app-stop.sh

set -euo pipefail

SERVICE_NAME="multimax"

echo "⏹️  Parando $SERVICE_NAME..."
if systemctl stop "$SERVICE_NAME"; then
    sleep 2
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ $SERVICE_NAME parado com sucesso"
    else
        echo "⚠️  $SERVICE_NAME ainda está rodando"
        systemctl status "$SERVICE_NAME"
    fi
else
    echo "❌ Erro ao parar $SERVICE_NAME"
    exit 1
fi
