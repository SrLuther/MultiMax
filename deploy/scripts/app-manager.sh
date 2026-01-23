#!/bin/bash

################################################################################
# MultiMax Application Manager
#
# Propósito: Gerenciar ciclo de vida da aplicação (start, stop, status, etc)
# Uso: ./app-manager.sh [start|stop|restart|status|logs]
#
# Nota: Requer variáveis de ambiente configuradas em .env
################################################################################

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
readonly PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"

# Cores
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_NC='\033[0m'

# Configuração padrão (sobrescreve .env)
MULTIMAX_HOME="${MULTIMAX_HOME:-/opt/multimax}"
MULTIMAX_PORT="${MULTIMAX_PORT:-5000}"
PYTHON_VENV="${MULTIMAX_HOME}/venv"
PID_FILE="/tmp/multimax.pid"
LOG_FILE="${MULTIMAX_HOME}/../logs/multimax.log"

# Funções
log_info() { echo -e "${COLOR_BLUE}[INFO]${COLOR_NC} $*"; }
log_success() { echo -e "${COLOR_GREEN}[✓]${COLOR_NC} $*"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_NC} $*" >&2; }

# Carregar .env se existir
if [[ -f "$MULTIMAX_HOME/.env" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$MULTIMAX_HOME/.env" | xargs -d '\n')
fi

cmd_start() {
    log_info "Iniciando MultiMax..."

    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        log_error "MultiMax já está em execução (PID: $(cat "$PID_FILE"))"
        return 1
    fi

    cd "$MULTIMAX_HOME"
    # shellcheck disable=SC1090,SC1091
    source "$PYTHON_VENV/bin/activate"

    mkdir -p "$(dirname "$LOG_FILE")"

    # Executar em background
    nohup python app.py >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        log_success "MultiMax iniciado (PID: $pid)"
        return 0
    else
        log_error "Erro ao iniciar MultiMax. Verifique os logs:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

cmd_stop() {
    log_info "Parando MultiMax..."

    if [[ ! -f "$PID_FILE" ]]; then
        log_error "Arquivo PID não encontrado. MultiMax pode não estar em execução."
        return 1
    fi

    local pid
    pid=$(cat "$PID_FILE")

    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "Processo $pid não está em execução"
        rm -f "$PID_FILE"
        return 1
    fi

    kill "$pid"
    sleep 2

    if ! kill -0 "$pid" 2>/dev/null; then
        log_success "MultiMax parado"
        rm -f "$PID_FILE"
    else
        log_error "Timeout ao parar MultiMax. Forçando..."
        kill -9 "$pid" || true
        rm -f "$PID_FILE"
    fi
}

cmd_restart() {
    log_info "Reiniciando MultiMax..."
    cmd_stop || true
    sleep 1
    cmd_start
}

cmd_status() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_error "MultiMax não está em execução (PID file não encontrado)"
        return 1
    fi

    local pid
    pid=$(cat "$PID_FILE")

    if kill -0 "$pid" 2>/dev/null; then
        log_success "MultiMax está em execução (PID: $pid)"
        log_info "Porta: $MULTIMAX_PORT"
        log_info "Home: $MULTIMAX_HOME"
        return 0
    else
        log_error "Processo $pid não está em execução"
        return 1
    fi
}

cmd_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        log_error "Arquivo de log não encontrado: $LOG_FILE"
        return 1
    fi

    tail -f "$LOG_FILE"
}

# Main
case "${1:-help}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    *)
        echo "Uso: $0 [start|stop|restart|status|logs]"
        exit 1
        ;;
esac
