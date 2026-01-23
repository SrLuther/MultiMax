#!/bin/bash

################################################################################
# MultiMax Deploy Setup Script - Ubuntu 24.04 LTS
#
# Propósito: Instalação completa, idempotente e automatizada do MultiMax
# Uso: sudo ./setup.sh [--skip-os-deps] [--skip-db] [--user=multimax]
#
# Características:
# - Detecta ambiente (servidor/desenvolvimento)
# - Instala dependências do SO via apt
# - Cria usuário não-root para execução
# - Configura variáveis de ambiente
# - Inicializa banco de dados
# - Prepara estrutura de diretórios
# - Idempotente: seguro executar múltiplas vezes
################################################################################

set -euo pipefail

# ============================================================================
# CONSTANTES E CONFIGURAÇÃO
# ============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly DEPLOY_CONFIG="$SCRIPT_DIR/config"
readonly DEPLOY_SCRIPTS="$SCRIPT_DIR/scripts"
readonly SYSTEMD_DIR="$SCRIPT_DIR/systemd"

# Cores para output
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_NC='\033[0m' # No Color

# Parâmetros padrão
MULTIMAX_USER="${MULTIMAX_USER:-multimax}"
MULTIMAX_GROUP="${MULTIMAX_GROUP:-multimax}"
MULTIMAX_HOME="${MULTIMAX_HOME:-/opt/multimax}"
MULTIMAX_DATA_DIR="${MULTIMAX_DATA_DIR:-/var/lib/multimax}"
PYTHON_VENV="${MULTIMAX_HOME}/venv"
SKIP_OS_DEPS=false
SKIP_DB_INIT=false

# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

log_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_NC} $*" >&2
}

log_success() {
    echo -e "${COLOR_GREEN}[✓]${COLOR_NC} $*" >&2
}

log_warn() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_NC} $*" >&2
}

log_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_NC} $*" >&2
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script deve ser executado como root (use: sudo ./setup.sh)"
        exit 1
    fi
}

check_os() {
    if ! grep -q "24.04" /etc/os-release && ! grep -q "22.04" /etc/os-release && ! grep -q "20.04" /etc/os-release; then
        log_warn "Script otimizado para Ubuntu 24.04/22.04/20.04. Sistema detectado:"
        cat /etc/os-release | grep "^VERSION=" >&2
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-os-deps)
                SKIP_OS_DEPS=true
                shift
                ;;
            --skip-db)
                SKIP_DB_INIT=true
                shift
                ;;
            --user=*)
                MULTIMAX_USER="${1#*=}"
                MULTIMAX_GROUP="$MULTIMAX_USER"
                shift
                ;;
            --home=*)
                MULTIMAX_HOME="${1#*=}"
                PYTHON_VENV="${MULTIMAX_HOME}/venv"
                shift
                ;;
            --data-dir=*)
                MULTIMAX_DATA_DIR="${1#*=}"
                shift
                ;;
            *)
                log_error "Argumento desconhecido: $1"
                echo "Uso: sudo $0 [--skip-os-deps] [--skip-db] [--user=multimax] [--home=/opt/multimax] [--data-dir=/var/lib/multimax]" >&2
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# ETAPAS PRINCIPAIS
# ============================================================================

step_check_environment() {
    log_info "Verificando ambiente..."

    check_root
    check_os

    if [[ ! -f "$PROJECT_ROOT/app.py" ]]; then
        log_error "app.py não encontrado em $PROJECT_ROOT. Você está no diretório correto?"
        exit 1
    fi

    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_error "requirements.txt não encontrado em $PROJECT_ROOT"
        exit 1
    fi

    log_success "Ambiente verificado"
}

step_install_os_dependencies() {
    if [[ "$SKIP_OS_DEPS" == true ]]; then
        log_warn "Pulando instalação de dependências do SO (--skip-os-deps)"
        return 0
    fi

    log_info "Instalando dependências do sistema operacional..."

    # Atualizar índice de pacotes
    apt-get update -qq

    # Dependências essenciais
    local packages=(
        python3.11
        python3.11-venv
        python3.11-dev
        python3-pip
        build-essential
        libpq-dev
        postgresql-client
        git
        curl
        wget
        nano
        net-tools
        htop
    )

    # Dependências para geração de PDFs/relatórios
    packages+=(
        libcairo2-dev
        libpango-1.0-0
        libpango-cairo-1.0-0
        libgdk-pixbuf2.0-0
    )

    # Nginx (recomendado para reverse proxy)
    packages+=(
        nginx
    )

    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg"; then
            log_info "Instalando: $pkg"
            DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" > /dev/null 2>&1
        fi
    done

    log_success "Dependências do SO instaladas"
}

step_create_user() {
    log_info "Verificando usuário '$MULTIMAX_USER'..."

    if id "$MULTIMAX_USER" &>/dev/null; then
        log_warn "Usuário '$MULTIMAX_USER' já existe"
    else
        log_info "Criando usuário '$MULTIMAX_USER'..."
        useradd -r -s /bin/bash -d "$MULTIMAX_HOME" -m -c "MultiMax Application" "$MULTIMAX_USER" || true
        log_success "Usuário criado"
    fi
}

step_create_directories() {
    log_info "Criando estrutura de diretórios..."

    # Diretórios da aplicação
    mkdir -p "$MULTIMAX_HOME"
    mkdir -p "$MULTIMAX_DATA_DIR"
    mkdir -p "$MULTIMAX_DATA_DIR/backups"
    mkdir -p "$MULTIMAX_DATA_DIR/logs"

    # Copiar código da aplicação (se não estiver lá)
    if [[ ! -f "$MULTIMAX_HOME/app.py" ]]; then
        log_info "Copiando código da aplicação para $MULTIMAX_HOME..."
        cp -r "$PROJECT_ROOT"/* "$MULTIMAX_HOME/"
        # Remover arquivos desnecessários para produção
        rm -rf "$MULTIMAX_HOME"/.git "$MULTIMAX_HOME"/.env.example "$MULTIMAX_HOME"/*.md
    fi

    # Permissões corretas
    chown -R "$MULTIMAX_USER:$MULTIMAX_GROUP" "$MULTIMAX_HOME"
    chown -R "$MULTIMAX_USER:$MULTIMAX_GROUP" "$MULTIMAX_DATA_DIR"
    chmod 755 "$MULTIMAX_HOME"
    chmod 755 "$MULTIMAX_DATA_DIR"
    chmod 700 "$MULTIMAX_DATA_DIR/backups"

    log_success "Diretórios criados com permissões corretas"
}

step_setup_python_environment() {
    log_info "Configurando ambiente Python (venv)..."

    if [[ ! -d "$PYTHON_VENV" ]]; then
        log_info "Criando venv em $PYTHON_VENV..."
        python3.11 -m venv "$PYTHON_VENV"
    fi

    # Ativar venv e instalar dependências
    # shellcheck disable=SC1090,SC1091
    source "$PYTHON_VENV/bin/activate"

    log_info "Atualizando pip, setuptools, wheel..."
    pip install --quiet --upgrade pip setuptools wheel

    log_info "Instalando dependências do projeto..."
    pip install --quiet -r "$PROJECT_ROOT/requirements.txt"

    # Permissões do venv
    chown -R "$MULTIMAX_USER:$MULTIMAX_GROUP" "$PYTHON_VENV"

    log_success "Ambiente Python configurado"
}

step_configure_environment() {
    log_info "Configurando variáveis de ambiente..."

    # Se .env não existe, criar a partir do exemplo
    local env_file="$MULTIMAX_HOME/.env"
    if [[ ! -f "$env_file" ]]; then
        log_info "Criando arquivo .env a partir do template..."

        # Copiar .env.example se existir, senão criar mínimo
        if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
            cp "$PROJECT_ROOT/.env.example" "$env_file"
        else
            cat > "$env_file" <<'ENVEOF'
# ============================================================================
# MultiMax Environment Configuration
# ============================================================================

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=CHANGE_ME_IN_PRODUCTION_$(openssl rand -hex 32)

# Server Configuration
MULTIMAX_PORT=5000
MULTIMAX_HOST=127.0.0.1

# Database Configuration
DATABASE_URL=postgresql+psycopg://multimax:CHANGE_PASSWORD@localhost:5432/multimax

# Application Data
MULTIMAX_DATA_DIR=/var/lib/multimax
DB_FILE_PATH=/var/lib/multimax/estoque.db

# Maintenance Mode
MAINTENANCE_MODE=false

# Keep-Alive (para servidores serverless)
KEEPALIVE_ENABLED=false
KEEPALIVE_URL=
KEEPALIVE_INTERVAL=300

# Logging
LOG_LEVEL=INFO
ENVEOF
        fi

        # Gerar SECRET_KEY seguro
        local secret_key
        secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" "$env_file"

        chown "$MULTIMAX_USER:$MULTIMAX_GROUP" "$env_file"
        chmod 600 "$env_file"  # Apenas owner pode ler (contém credenciais)

        log_warn "Arquivo .env criado. EDITE com suas credenciais antes de executar!"
        log_warn "Arquivo: $env_file"
    else
        log_success "Arquivo .env já existe"
    fi
}

step_initialize_database() {
    if [[ "$SKIP_DB_INIT" == true ]]; then
        log_warn "Pulando inicialização de banco de dados (--skip-db)"
        return 0
    fi

    log_info "Inicializando banco de dados..."

    # Verificar se há migrations
    if [[ -d "$MULTIMAX_HOME/migrations" ]]; then
        log_info "Executando migrations Alembic..."
        cd "$MULTIMAX_HOME"
        # shellcheck disable=SC1090,SC1091
        source "$PYTHON_VENV/bin/activate"
        alembic upgrade head || log_warn "Erro ao executar migrations (pode ser esperado em primeira instalação)"
    else
        log_warn "Diretório 'migrations' não encontrado. Criação de tabelas será feita pela aplicação."
    fi

    log_success "Banco de dados inicializado"
}

step_install_systemd_service() {
    log_info "Instalando serviço systemd..."

    if [[ ! -f "$SYSTEMD_DIR/multimax.service" ]]; then
        log_warn "Arquivo $SYSTEMD_DIR/multimax.service não encontrado"
        log_info "Você pode criá-lo manualmente usando deploy/docs/SYSTEMD.md como referência"
        return 0
    fi

    # Copiar e customizar o arquivo de serviço
    local service_dest="/etc/systemd/system/multimax.service"
    cp "$SYSTEMD_DIR/multimax.service" "$service_dest"

    # Customizar caminhos se necessário
    sed -i "s|USER=.*|USER=$MULTIMAX_USER|g" "$service_dest"
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$MULTIMAX_HOME|g" "$service_dest"
    sed -i "s|ExecStart=.*|ExecStart=$PYTHON_VENV/bin/python app.py|g" "$service_dest"

    # Registrar o serviço
    systemctl daemon-reload
    systemctl enable multimax.service || true

    log_success "Serviço systemd instalado e habilitado"
    log_info "Para iniciar: systemctl start multimax"
}

step_configure_nginx() {
    log_info "Verificando configuração Nginx..."

    if [[ ! -f "/etc/nginx/sites-available/multimax" ]]; then
        log_info "Arquivo de config Nginx não encontrado. Criando template..."

        cat > "/etc/nginx/sites-available/multimax" <<'NGINXEOF'
# MultiMax Nginx Configuration
# Habilite com: sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/
# E recarregue com: sudo systemctl reload nginx

upstream multimax_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name _;  # Mude para seu domínio

    # Limites de upload
    client_max_body_size 100M;

    # Logs
    access_log /var/log/nginx/multimax_access.log;
    error_log /var/log/nginx/multimax_error.log;

    # Reverse proxy
    location / {
        proxy_pass http://multimax_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # Static files (se não usar CDN)
    location /static/ {
        alias /opt/multimax/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
NGINXEOF

        log_warn "Template Nginx criado em /etc/nginx/sites-available/multimax"
        log_info "Para habilitar: sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/"
    fi
}

step_final_checks() {
    log_info "Executando verificações finais..."

    # Verificar que aplicação pode ser importada
    cd "$MULTIMAX_HOME"
    # shellcheck disable=SC1090,SC1091
    source "$PYTHON_VENV/bin/activate"

    if python3 -c "from multimax import create_app; create_app()" 2>/dev/null; then
        log_success "Aplicação importada com sucesso"
    else
        log_warn "Erro ao importar aplicação. Verifique as dependências."
    fi

    # Resumo
    log_success "Instalação concluída!"
}

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

main() {
    parse_args "$@"

    echo ""
    log_info "════════════════════════════════════════════════════════════════"
    log_info "  MultiMax Deploy Setup - Ubuntu 24.04 LTS"
    log_info "════════════════════════════════════════════════════════════════"
    echo ""
    log_info "Configurações:"
    log_info "  Usuário: $MULTIMAX_USER"
    log_info "  Home: $MULTIMAX_HOME"
    log_info "  Data: $MULTIMAX_DATA_DIR"
    log_info "  Python venv: $PYTHON_VENV"
    echo ""

    # Executar etapas
    step_check_environment
    step_install_os_dependencies
    step_create_user
    step_create_directories
    step_setup_python_environment
    step_configure_environment
    step_initialize_database
    step_install_systemd_service
    step_configure_nginx
    step_final_checks

    echo ""
    log_success "════════════════════════════════════════════════════════════════"
    log_success "  Instalação finalizada com sucesso!"
    log_success "════════════════════════════════════════════════════════════════"
    echo ""
    log_info "Próximos passos:"
    log_info "  1. Editar variáveis de ambiente:"
    log_info "     sudo nano $MULTIMAX_HOME/.env"
    log_info ""
    log_info "  2. Habilitar Nginx (opcional):"
    log_info "     sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/"
    log_info "     sudo systemctl reload nginx"
    log_info ""
    log_info "  3. Iniciar aplicação:"
    log_info "     sudo systemctl start multimax"
    log_info "     sudo systemctl status multimax"
    echo ""
}

# Executar
main "$@"
