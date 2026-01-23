#!/bin/bash
# MultiMax - Ver Logs em Tempo Real
# Uso: ./scripts/app-logs.sh [lines]

set -euo pipefail

LINES="${1:-50}"
SERVICE_NAME="multimax"
LOG_FILE="/var/log/multimax/app.log"

echo "📋 Últimas $LINES linhas dos logs da aplicação:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -f "$LOG_FILE" ]]; then
    tail -n "$LINES" "$LOG_FILE"
else
    echo "⚠️  Log file não encontrado: $LOG_FILE"
    echo ""
    echo "Tentando ver logs do systemd..."
    journalctl -u "$SERVICE_NAME" -n "$LINES"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Para ver logs em tempo real, use:"
echo "  journalctl -u $SERVICE_NAME -f"
