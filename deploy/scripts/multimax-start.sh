#!/bin/bash
# MultiMax - Iniciar Aplicação
# Uso: sudo systemctl start multimax
# ou: ./scripts/app-start.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/multimax}"
SERVICE_NAME="multimax"

echo "▶️  Iniciando $SERVICE_NAME..."
if systemctl start "$SERVICE_NAME"; then
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ $SERVICE_NAME iniciado com sucesso"
        systemctl status "$SERVICE_NAME"
    else
        echo "❌ Falha ao iniciar $SERVICE_NAME"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
else
    echo "❌ Erro ao iniciar $SERVICE_NAME"
    exit 1
fi
