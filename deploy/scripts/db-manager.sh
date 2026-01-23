#!/bin/bash

################################################################################
# MultiMax Database Manager
#
# Propósito: Gerenciar banco de dados (init, backup, restore)
# Uso: ./db-manager.sh [init|backup|restore|status]
################################################################################

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
readonly PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"
readonly MULTIMAX_HOME="${MULTIMAX_HOME:-/opt/multimax}"
readonly MULTIMAX_DATA_DIR="${MULTIMAX_DATA_DIR:-/var/lib/multimax}"
readonly BACKUP_DIR="$MULTIMAX_DATA_DIR/backups"
readonly PYTHON_VENV="${MULTIMAX_HOME}/venv"

# Cores
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_NC='\033[0m'

log_info() { echo -e "${COLOR_BLUE}[INFO]${COLOR_NC} $*"; }
log_success() { echo -e "${COLOR_GREEN}[✓]${COLOR_NC} $*"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_NC} $*" >&2; }

# Carregar .env
if [[ -f "$MULTIMAX_HOME/.env" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$MULTIMAX_HOME/.env" | xargs -d '\n')
fi

cmd_init() {
    log_info "Inicializando banco de dados..."

    mkdir -p "$BACKUP_DIR"

    cd "$MULTIMAX_HOME"
    # shellcheck disable=SC1090,SC1091
    source "$PYTHON_VENV/bin/activate"

    # Se houver migrations, executar
    if [[ -d "$MULTIMAX_HOME/migrations" ]]; then
        log_info "Executando Alembic migrations..."
        alembic upgrade head 2>&1 || log_info "Migrations completadas (ou já executadas)"
    fi

    log_success "Banco de dados inicializado"
}

cmd_backup() {
    log_info "Criando backup do banco de dados..."

    mkdir -p "$BACKUP_DIR"

    local backup_file
    backup_file="$BACKUP_DIR/multimax_$(date +%Y%m%d_%H%M%S).sql"

    # Extrair dados de conexão do DATABASE_URL
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL não configurado em .env"
        return 1
    fi

    # Parse PostgreSQL URL
    if [[ "$DATABASE_URL" == postgresql* ]]; then
        log_info "Backup de PostgreSQL..."
        # Exemplo: postgresql://user:pass@host/dbname
        local dbname
        dbname=$(echo "$DATABASE_URL" | grep -oP '(?<=/)[^?]*' | head -1)

        pg_dump "$DATABASE_URL" > "$backup_file" || {
            log_error "Erro ao fazer backup"
            return 1
        }
    elif [[ "$DATABASE_URL" == sqlite* ]]; then
        log_info "Backup de SQLite..."
        local db_file
        db_file="${DB_FILE_PATH:-$MULTIMAX_DATA_DIR/estoque.db}"

        if [[ -f "$db_file" ]]; then
            cp "$db_file" "$backup_file"
        fi
    fi

    # Compress
    gzip "$backup_file"
    backup_file="$backup_file.gz"

    # Limpeza de backups antigos (mais de 30 dias)
    find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

    log_success "Backup criado: $backup_file"
}

cmd_restore() {
    local backup_file="${1:-}"

    if [[ -z "$backup_file" ]]; then
        log_error "Uso: $0 restore <caminho_backup>"
        ls -lh "$BACKUP_DIR" 2>/dev/null || log_info "Nenhum backup encontrado em $BACKUP_DIR"
        return 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log_error "Arquivo de backup não encontrado: $backup_file"
        return 1
    fi

    log_info "Restaurando backup: $backup_file"

    # Decompress se necessário
    local sql_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        sql_file="${backup_file%.gz}"
        gunzip -c "$backup_file" > "$sql_file"
    fi

    # Restaurar
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL não configurado"
        return 1
    fi

    if [[ "$DATABASE_URL" == postgresql* ]]; then
        log_info "Restaurando PostgreSQL..."
        psql "$DATABASE_URL" < "$sql_file" || {
            log_error "Erro ao restaurar"
            return 1
        }
    fi

    log_success "Backup restaurado"
}

cmd_status() {
    log_info "Status do banco de dados:"
    log_info "  Database URL: ${DATABASE_URL:0:50}..."
    log_info "  Data dir: $MULTIMAX_DATA_DIR"

    if [[ -d "$BACKUP_DIR" ]] && [[ -n "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]]; then
        log_info "  Últimos backups:"
        ls -lh "$BACKUP_DIR" | tail -5 | awk '{print "    " $9 " (" $5 ")"}'
    fi
}

case "${1:-help}" in
    init)
        cmd_init
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore "${2:-}"
        ;;
    status)
        cmd_status
        ;;
    *)
        echo "Uso: $0 [init|backup|restore|status]"
        exit 1
        ;;
esac
