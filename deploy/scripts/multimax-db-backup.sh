#!/bin/bash
# MultiMax - Backup do Banco de Dados
# Uso: ./scripts/db-backup.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/multimax}"
BACKUP_DIR="$APP_DIR/backups"
DB_NAME="${DB_NAME:-multimax}"
DB_USER="${DB_USER:-multimax}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/multimax_db_${TIMESTAMP}.sql.gz"

# Cores
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}💾 Iniciando backup do banco de dados...${NC}"

if pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup concluído com sucesso${NC}"
    echo -e "${GREEN}Arquivo: $BACKUP_FILE${NC}"
    echo -e "${GREEN}Tamanho: $SIZE${NC}"

    # Manter apenas últimos 7 backups
    echo -e "${BLUE}Limpando backups antigos (mantendo últimos 7)...${NC}"
    ls -t "$BACKUP_DIR"/multimax_db_*.sql.gz | tail -n +8 | xargs -r rm
    echo -e "${GREEN}✓ Limpeza concluída${NC}"
else
    echo -e "${RED}✗ Falha ao fazer backup${NC}"
    exit 1
fi
