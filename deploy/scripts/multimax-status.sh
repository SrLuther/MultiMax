#!/bin/bash
# MultiMax - Verificar Status do Sistema
# Uso: ./scripts/app-status.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/multimax}"
SERVICE_NAME="multimax"

# Cores
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   MultiMax System Status${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Status da aplicação
echo ""
echo -e "${YELLOW}📦 Aplicação:${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "  ${GREEN}✓ Rodando${NC}"
    systemctl status "$SERVICE_NAME" --no-pager
else
    echo -e "  ${RED}✗ Parada${NC}"
fi

# Status do PostgreSQL
echo ""
echo -e "${YELLOW}🗄️  PostgreSQL:${NC}"
if systemctl is-active --quiet postgresql; then
    echo -e "  ${GREEN}✓ Rodando${NC}"

    # Conexão ao banco
    if sudo -u postgres psql -l &>/dev/null; then
        echo -e "  ${GREEN}✓ Banco de dados acessível${NC}"
    else
        echo -e "  ${RED}✗ Erro ao acessar banco de dados${NC}"
    fi
else
    echo -e "  ${RED}✗ Parada${NC}"
fi

# Status do Nginx
echo ""
echo -e "${YELLOW}🌐 Nginx:${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "  ${GREEN}✓ Rodando${NC}"
else
    echo -e "  ${RED}✗ Parada${NC}"
fi

# Uso de recursos
echo ""
echo -e "${YELLOW}📊 Recursos:${NC}"

# Verificar se a aplicação está rodando
if pgrep -f "python.*app" > /dev/null; then
    PID=$(pgrep -f "python.*app" | head -1)
    echo "  PID: $PID"

    if command -v ps &> /dev/null; then
        ps aux | grep $PID | grep -v grep | awk '{printf "  CPU: %.1f%% | MEM: %.1f%%\n", $3, $4}'
    fi
fi

# Espaço em disco
echo ""
echo -e "${YELLOW}💾 Espaço em Disco:${NC}"
df -h "$APP_DIR" | tail -1 | awk '{printf "  Usado: %s | Disponível: %s (%.1f%%)\n", $3, $4, ($3/($3+$4)*100)}'

# Últimos logs
echo ""
echo -e "${YELLOW}📋 Últimas linhas do log:${NC}"
journalctl -u "$SERVICE_NAME" -n 5 --no-pager 2>/dev/null | sed 's/^/  /'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
