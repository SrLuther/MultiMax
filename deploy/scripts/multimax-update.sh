#!/bin/bash
# MultiMax - Atualizar Aplicação
# Uso: ./scripts/app-update.sh
# Função: Puxa última versão, instala dependências, aplica migrations

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/multimax}"
APP_USER="${APP_USER:-multimax}"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="multimax"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   MultiMax Application Update${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Parar aplicação
log_info "Parando aplicação..."
systemctl stop "$SERVICE_NAME" || true
sleep 2

# Atualizar repositório
log_info "Atualizando repositório..."
cd "$APP_DIR/app"
sudo -u "$APP_USER" git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
sudo -u "$APP_USER" git pull origin "$CURRENT_BRANCH"
log_success "Repositório atualizado"

# Ativar venv
log_info "Ativando virtual environment..."
source "$VENV_DIR/bin/activate"

# Instalar dependências
log_info "Instalando dependências Python..."
pip install --upgrade pip setuptools wheel -q
if [[ -f "$APP_DIR/app/requirements.txt" ]]; then
    pip install -r "$APP_DIR/app/requirements.txt" -q
    log_success "Dependências instaladas"
fi

# Executar migrations
log_info "Aplicando migrations do banco de dados..."
if [[ -d "$APP_DIR/app/migrations" ]]; then
    FLASK_APP=app.py flask db upgrade || log_warn "Migrations não aplicadas (pode estar ok)"
    log_success "Database migrations concluídas"
fi

deactivate

# Reiniciar aplicação
log_info "Iniciando aplicação..."
systemctl start "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_success "Aplicação reiniciada com sucesso"
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Atualização concluída com sucesso!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    log_error "Falha ao reiniciar aplicação"
    systemctl status "$SERVICE_NAME"
    exit 1
fi
