#!/bin/bash
#==============================================================================
# MultiMax - Setup Script for Ubuntu 24.04 LTS
#==============================================================================
# Propósito: Instalação idempotente completa do MultiMax em servidor Linux
# Funcionalidades: Sistema de arquivos, dependências, banco de dados,
#                  aplicação, serviços systemd, nginx, SSL/TLS
#==============================================================================

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuração
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/var/log/multimax-setup.log"
APP_DIR="${APP_DIR:-/opt/multimax}"
APP_USER="${APP_USER:-multimax}"
APP_GROUP="${APP_GROUP:-multimax}"
VENV_DIR="${APP_DIR}/venv"
PYTHON_VERSION="3.11"

# Inicializar log
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

#==============================================================================
# Funções Auxiliares
#==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script deve ser executado como root (use: sudo bash setup.sh)"
        exit 1
    fi
}

command_exists() {
    command -v "$1" &> /dev/null
}

#==============================================================================
# 1. Validações Iniciais
#==============================================================================

validate_environment() {
    log_info "Validando ambiente..."

    # Verificar SO
    if ! grep -qi "ubuntu" /etc/os-release; then
        log_error "Este script é otimizado para Ubuntu. Use em sua conta e risco."
    fi

    # Verificar espaço em disco (mínimo 5GB)
    AVAILABLE_SPACE=$(df /opt 2>/dev/null | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -lt 5242880 ]]; then
        log_error "Espaço insuficiente em /opt (mínimo 5GB necessário)"
        exit 1
    fi

    log_success "Ambiente validado"
}

#==============================================================================
# 2. Atualizar Sistema
#==============================================================================

update_system() {
    log_info "Atualizando sistema operacional..."
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "Sistema atualizado"
}

#==============================================================================
# 3. Instalar Dependências do Sistema
#==============================================================================

install_system_dependencies() {
    log_info "Instalando dependências do sistema..."

    # Pacotes essenciais
    apt-get install -y -qq \
        build-essential \
        curl \
        git \
        wget \
        sudo \
        nano \
        vim \
        htop \
        net-tools \
        unzip \
        zip \
        tar \
        jq

    # Python e ferramentas
    apt-get install -y -qq \
        "python${PYTHON_VERSION}" \
        "python${PYTHON_VERSION}-venv" \
        "python${PYTHON_VERSION}-dev" \
        "python${PYTHON_VERSION}-distutils" \
        pip

    # Banco de dados
    apt-get install -y -qq \
        postgresql \
        postgresql-contrib \
        postgresql-client

    # Web server
    apt-get install -y -qq \
        nginx \
        ssl-cert

    # Sistema de dependências
    apt-get install -y -qq \
        libpq-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libpangoft2-1.0-0

    log_success "Dependências do sistema instaladas"
}

#==============================================================================
# 4. Criar Usuário da Aplicação
#==============================================================================

create_app_user() {
    log_info "Criando usuário da aplicação: $APP_USER"

    if id "$APP_USER" &>/dev/null; then
        log_warn "Usuário $APP_USER já existe"
    else
        useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
        log_success "Usuário $APP_USER criado"
    fi

    # Adicionar sudo sem senha para deploy automático (OPCIONAL)
    # echo "$APP_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl" | visudo -f /etc/sudoers.d/multimax
}

#==============================================================================
# 5. Preparar Diretórios da Aplicação
#==============================================================================

prepare_directories() {
    log_info "Preparando estrutura de diretórios..."

    # Criar diretórios principais
    mkdir -p "$APP_DIR"/{.env,logs,tmp,data,backups}
    mkdir -p "$APP_DIR/app"

    # Configurar permissões
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
    chmod 750 "$APP_DIR"
    chmod 755 "$APP_DIR/app"

    # Criar diretório de logs com permissões apropriadas
    mkdir -p /var/log/multimax
    chown "$APP_USER:$APP_GROUP" /var/log/multimax
    chmod 755 /var/log/multimax

    log_success "Diretórios preparados em $APP_DIR"
}

#==============================================================================
# 6. Clonar/Sincronizar Repositório
#==============================================================================

clone_or_update_repository() {
    log_info "Sincronizando repositório da aplicação..."

    REPO_URL="${REPO_URL:-https://github.com/SrLuther/MultiMax.git}"
    REPO_BRANCH="${REPO_BRANCH:-main}"

    if [[ -d "$APP_DIR/app/.git" ]]; then
        log_info "Repositório já existe, atualizando..."
        cd "$APP_DIR/app"
        sudo -u "$APP_USER" git fetch origin
        sudo -u "$APP_USER" git checkout "$REPO_BRANCH"
        sudo -u "$APP_USER" git pull origin "$REPO_BRANCH"
    else
        log_info "Clonando repositório..."
        cd "$APP_DIR"
        sudo -u "$APP_USER" git clone --branch "$REPO_BRANCH" "$REPO_URL" app
    fi

    log_success "Repositório sincronizado"
}

#==============================================================================
# 7. Configurar Ambiente Python
#==============================================================================

setup_python_environment() {
    log_info "Configurando ambiente Python..."

    # Criar virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        sudo -u "$APP_USER" python"${PYTHON_VERSION}" -m venv "$VENV_DIR"
        log_info "Virtual environment criado"
    fi

    # Ativar venv e instalar dependências
    source "$VENV_DIR/bin/activate"

    # Atualizar pip
    pip install --upgrade pip setuptools wheel -q

    # Instalar dependências da aplicação
    if [[ -f "$APP_DIR/app/requirements.txt" ]]; then
        pip install -r "$APP_DIR/app/requirements.txt" -q
        log_success "Dependências Python instaladas"
    fi

    deactivate
}

#==============================================================================
# 8. Configurar PostgreSQL
#==============================================================================

setup_postgresql() {
    log_info "Configurando PostgreSQL..."

    # Iniciar PostgreSQL se não estiver rodando
    if ! systemctl is-active --quiet postgresql; then
        systemctl start postgresql
        systemctl enable postgresql
        log_info "PostgreSQL iniciado"
    fi

    # Criar banco de dados e usuário
    sudo -u postgres psql <<EOF || true
-- Criar usuário (idempotente)
DO \$\$
BEGIN
    CREATE USER multimax WITH PASSWORD '${DB_PASSWORD:-multimax123}';
EXCEPTION WHEN DUPLICATE_OBJECT THEN
    ALTER USER multimax WITH PASSWORD '${DB_PASSWORD:-multimax123}';
END
\$\$;

-- Criar banco de dados
CREATE DATABASE multimax OWNER multimax TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';

-- Conceder privilégios
ALTER DATABASE multimax OWNER TO multimax;
GRANT ALL PRIVILEGES ON DATABASE multimax TO multimax;
EOF

    log_success "PostgreSQL configurado"
}

#==============================================================================
# 9. Configurar Arquivos de Ambiente
#==============================================================================

setup_environment_files() {
    log_info "Configurando arquivos de ambiente..."

    ENV_FILE="$APP_DIR/.env"

    if [[ ! -f "$ENV_FILE" ]]; then
        cat > "$ENV_FILE" <<'EOF'
# MultiMax Application Configuration
# Gerado por setup.sh em $(date)

# Flask Configuration
FLASK_ENV=production
DEBUG=false
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Database
DATABASE_URL=postgresql://multimax:multimax123@localhost:5432/multimax
DB_POOL_SIZE=10
DB_POOL_RECYCLE=3600

# Application
HOST=127.0.0.1
PORT=5000
WORKERS=4

# Security
MAX_CONTENT_LENGTH=16777216
SESSION_TIMEOUT=3600
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/multimax/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10

# Features
KEEPALIVE_ENABLED=false
KEEPALIVE_INTERVAL=300

# Email (opcional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# WhatsApp (opcional)
WHATSAPP_ENABLED=false
WHATSAPP_API_URL=
WHATSAPP_API_KEY=
EOF

        chown "$APP_USER:$APP_GROUP" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log_success "Arquivo .env criado em $ENV_FILE"
        log_warn "⚠️  IMPORTANTE: Edite $ENV_FILE com suas configurações reais!"
    else
        log_warn ".env já existe, não foi sobrescrito"
    fi
}

#==============================================================================
# 10. Inicializar Banco de Dados
#==============================================================================

initialize_database() {
    log_info "Inicializando banco de dados..."

    source "$VENV_DIR/bin/activate"
    cd "$APP_DIR/app"

    # Verificar se há migrations pendentes
    if [[ -d "migrations" ]] && [[ -f "migrations/env.py" ]]; then
        FLASK_APP=app.py flask db upgrade || log_error "Erro ao aplicar migrations"
    fi

    deactivate
    log_success "Banco de dados inicializado"
}

#==============================================================================
# 11. Instalar Scripts de Operação
#==============================================================================

install_operation_scripts() {
    log_info "Instalando scripts de operação..."

    # Copiar scripts
    cp "$SCRIPT_DIR/scripts"/*.sh /usr/local/bin/ 2>/dev/null || true

    # Tornar executáveis
    chmod +x /usr/local/bin/multimax-*.sh

    log_success "Scripts de operação instalados"
}

#==============================================================================
# 12. Configurar Systemd Service
#==============================================================================

setup_systemd_service() {
    log_info "Configurando systemd service..."

    cat > /etc/systemd/system/multimax.service <<EOF
[Unit]
Description=MultiMax Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR/app
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_DIR/bin/python -m waitress --host=127.0.0.1 --port=5000 app:app
ExecReload=/bin/kill -HUP \$MAINPID
ExecStop=/bin/kill -TERM \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
SyslogIdentifier=multimax

# Restart policy
Restart=on-failure
RestartSec=10

# Resource limits
MemoryMax=512M
TasksMax=256

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_FILE

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable multimax.service
    log_success "Systemd service configurado"
}

#==============================================================================
# 13. Configurar Nginx
#==============================================================================

setup_nginx() {
    log_info "Configurando nginx..."

    # Backup de configuração existente
    if [[ -f /etc/nginx/sites-enabled/default ]]; then
        cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup
        rm /etc/nginx/sites-enabled/default
    fi

    # Criar configuração do MultiMax
    cat > /etc/nginx/sites-available/multimax <<'EOF'
upstream multimax_backend {
    server 127.0.0.1:5000 fail_timeout=0;
}

# Redirecionar HTTP para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Health check endpoint (sem HTTPS)
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Redirecionar tudo mais para HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name YOUR_DOMAIN_HERE;

    # SSL Configuration (ajustar após gerar certificados)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/multimax_access.log combined;
    error_log /var/log/nginx/multimax_error.log;

    # Client limits
    client_max_body_size 16M;
    client_body_timeout 30s;
    client_header_timeout 30s;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    # Proxy settings
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://multimax_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /opt/multimax/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Ativar site
    ln -sf /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/multimax || true

    # Teste de sintaxe
    if nginx -t &>/dev/null; then
        systemctl restart nginx
        log_success "Nginx configurado"
    else
        log_error "Erro na configuração do nginx"
        return 1
    fi
}

#==============================================================================
# 14. Gerar Certificados SSL Self-Signed (desenvolvimento)
#==============================================================================

setup_ssl_dev() {
    log_info "Gerando certificados SSL auto-assinados (desenvolvimento)..."

    mkdir -p /etc/nginx/ssl

    if [[ ! -f /etc/nginx/ssl/key.pem ]] || [[ ! -f /etc/nginx/ssl/cert.pem ]]; then
        openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/ssl/key.pem \
            -out /etc/nginx/ssl/cert.pem -days 365 -nodes \
            -subj "/C=BR/ST=State/L=City/O=MultiMax/CN=localhost"

        chmod 600 /etc/nginx/ssl/key.pem
        chmod 644 /etc/nginx/ssl/cert.pem

        log_success "Certificados SSL criados (APENAS DESENVOLVIMENTO)"
    fi
}

#==============================================================================
# 15. Testes de Sanidade
#==============================================================================

sanity_checks() {
    log_info "Executando testes de sanidade..."

    local errors=0

    # PostgreSQL
    if ! sudo -u postgres psql -l &>/dev/null; then
        log_error "PostgreSQL não está respondendo"
        ((errors++))
    fi

    # Python virtual environment
    if [[ ! -f "$VENV_DIR/bin/python" ]]; then
        log_error "Virtual environment não está configurado"
        ((errors++))
    fi

    # Permissões
    if [[ ! -d "$APP_DIR/app" ]]; then
        log_error "Diretório da aplicação não está preparado"
        ((errors++))
    fi

    # Nginx
    if ! nginx -t &>/dev/null; then
        log_error "Configuração nginx inválida"
        ((errors++))
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Todos os testes de sanidade passaram"
        return 0
    else
        log_error "$errors teste(s) falharam"
        return 1
    fi
}

#==============================================================================
# 16. Resumo e Próximos Passos
#==============================================================================

print_summary() {
    cat <<EOF

${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}
${GREEN}║           ✓ Setup do MultiMax Concluído com Sucesso            ║${NC}
${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}

📍 Aplicação instalada em: ${BLUE}$APP_DIR${NC}
👤 Usuário da aplicação: ${BLUE}$APP_USER${NC}
🗄️  Banco de dados: ${BLUE}multimax (PostgreSQL)${NC}
🌐 Nginx configurado para proxy reverso
🔐 SSL/TLS auto-assinado (DESENVOLVIMENTO APENAS)
🔧 Systemd service pronto para inicialização

${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${YELLOW}⚠️  PRÓXIMAS ETAPAS OBRIGATÓRIAS:${NC}
${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

1️⃣  Editar configurações:
    ${BLUE}sudo nano $ENV_FILE${NC}
    - Alterar SECRET_KEY
    - Configurar DATABASE_URL se necessário
    - Adicionar domínio real em MAIL_* e WHATSAPP_*

2️⃣  Configurar Nginx com seu domínio:
    ${BLUE}sudo nano /etc/nginx/sites-available/multimax${NC}
    - Alterar YOUR_DOMAIN_HERE para seu domínio real

3️⃣  Gerar certificado SSL válido (Let's Encrypt recomendado):
    ${BLUE}sudo apt-get install -y certbot python3-certbot-nginx${NC}
    ${BLUE}sudo certbot certonly --nginx -d seu-dominio.com${NC}

4️⃣  Iniciação da aplicação:
    ${BLUE}sudo systemctl start multimax${NC}
    ${BLUE}sudo systemctl status multimax${NC}

5️⃣  Verificar logs:
    ${BLUE}sudo journalctl -u multimax -f${NC}
    ${BLUE}tail -f $LOG_FILE${NC}

${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${YELLOW}📋 OPERAÇÕES DISPONÍVEIS:${NC}
${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

${BLUE}multimax-start.sh${NC}          - Iniciar aplicação
${BLUE}multimax-stop.sh${NC}           - Parar aplicação
${BLUE}multimax-restart.sh${NC}        - Reiniciar aplicação
${BLUE}multimax-logs.sh${NC}           - Ver logs em tempo real
${BLUE}multimax-update.sh${NC}         - Atualizar aplicação
${BLUE}multimax-db-backup.sh${NC}      - Fazer backup do banco

${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${YELLOW}📞 SUPORTE E TROUBLESHOOTING:${NC}
${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

Log de setup: ${BLUE}$LOG_FILE${NC}
Logs da app: ${BLUE}/var/log/multimax/app.log${NC}
Logs nginx: ${BLUE}/var/log/nginx/multimax_*.log${NC}

${GREEN}✓ Obrigado por usar o MultiMax!${NC}

EOF
}

#==============================================================================
# Main Execution Flow
#==============================================================================

main() {
    log_info "=== Iniciando Setup do MultiMax para Ubuntu 24.04 LTS ==="
    log_info "Log completo disponível em: $LOG_FILE"

    check_root
    validate_environment
    update_system
    install_system_dependencies
    create_app_user
    prepare_directories
    clone_or_update_repository
    setup_python_environment
    setup_postgresql
    setup_environment_files
    initialize_database
    install_operation_scripts
    setup_systemd_service
    setup_nginx
    setup_ssl_dev

    if sanity_checks; then
        print_summary
        log_success "=== Setup concluído com sucesso ==="
        exit 0
    else
        log_error "=== Setup concluído com erros ==="
        exit 1
    fi
}

# Executar se for chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
