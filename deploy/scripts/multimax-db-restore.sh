#!/bin/bash
# MultiMax - Restaurar Banco de Dados
# Uso: ./scripts/db-restore.sh <arquivo-backup.sql.gz>

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "❌ Uso: $0 <arquivo-backup.sql.gz>"
    echo ""
    echo "Exemplo:"
    echo "  $0 backups/multimax_db_20240115_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-multimax}"
DB_USER="${DB_USER:-multimax}"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "❌ Arquivo de backup não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  Atenção: Isto VAI SOBRESCREVER o banco de dados!"
read -p "Confirme digitando 'SIM': " confirm

if [[ "$confirm" != "SIM" ]]; then
    echo "❌ Operação cancelada"
    exit 1
fi

echo "💾 Restaurando banco de dados de: $BACKUP_FILE"

# Interromper aplicação
echo "Parando aplicação..."
systemctl stop multimax || true

# Restaurar banco
if gunzip -c "$BACKUP_FILE" | psql -U "$DB_USER" "$DB_NAME"; then
    echo "✅ Restauração concluída com sucesso"
    systemctl start multimax
else
    echo "❌ Falha ao restaurar banco de dados"
    systemctl start multimax || true
    exit 1
fi
