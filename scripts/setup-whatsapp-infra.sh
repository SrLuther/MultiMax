#!/bin/bash
#
# setup-whatsapp-infra.sh
# Script de automação para configurar infraestrutura do WhatsApp Service no MultiMax
#
# Uso: sudo ./scripts/setup-whatsapp-infra.sh
#
# Autor: MultiMax Team
# Data: 2026-01-22
#

set -e  # Parar em qualquer erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variáveis de configuração
MULTIMAX_USER="multimax"
INSTALL_DIR="/opt/multimax/whatsapp-service"
SERVICE_NAME="whatsapp-service"
DOMAIN="www.multimax.tec.br"
MULTIMAX_PORT="5000"
WHATSAPP_PORT="3001"

# Funções de output
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════╗
║  WhatsApp Service Infrastructure Setup - MultiMax   ║
║                                                      ║
║  Este script irá configurar:                        ║
║  • Node.js 18+ (se necessário)                      ║
║  • Nginx com proxy reverso                          ║
║  • Serviço systemd para WhatsApp                    ║
║  • Usuário e diretórios dedicados                   ║
╚══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
   error "Este script precisa ser executado como root (sudo)"
   exit 1
fi

success "Executando como root"

# Detectar SO
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    info "Sistema detectado: $OS $VERSION"
else
    error "Sistema operacional não suportado"
    exit 1
fi

# Validar SO suportado
if [[ "$OS" != "ubuntu" ]] && [[ "$OS" != "debian" ]]; then
    warning "Este script foi testado apenas em Ubuntu/Debian"
    read -p "Continuar mesmo assim? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. INSTALAR NODE.JS
info "Verificando instalação do Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ $NODE_VERSION -ge 18 ]]; then
        success "Node.js $(node -v) já instalado"
    else
        warning "Node.js versão antiga detectada: $(node -v)"
        info "Instalando Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
        success "Node.js $(node -v) instalado"
    fi
else
    info "Instalando Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
    success "Node.js $(node -v) instalado"
fi

# 2. INSTALAR NGINX
info "Verificando instalação do Nginx..."
if command -v nginx &> /dev/null; then
    success "Nginx $(nginx -v 2>&1 | cut -d'/' -f2) já instalado"
else
    info "Instalando Nginx..."
    apt-get update -qq
    apt-get install -y nginx
    systemctl enable nginx
    success "Nginx instalado e habilitado"
fi

# 3. CRIAR USUÁRIO DEDICADO
info "Configurando usuário $MULTIMAX_USER..."
if id "$MULTIMAX_USER" &>/dev/null; then
    success "Usuário $MULTIMAX_USER já existe"
else
    useradd -r -m -s /bin/bash "$MULTIMAX_USER"
    success "Usuário $MULTIMAX_USER criado"
fi

# 4. CRIAR DIRETÓRIO DO SERVIÇO
info "Criando diretório $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
chown "$MULTIMAX_USER:$MULTIMAX_USER" "$INSTALL_DIR"
success "Diretório criado e permissões configuradas"

# 5. VERIFICAR SE CÓDIGO EXISTE
if [[ ! -f "./whatsapp-service/index.js" ]]; then
    error "Arquivo whatsapp-service/index.js não encontrado"
    error "Execute este script da raiz do projeto MultiMax"
    exit 1
fi

# 6. COPIAR CÓDIGO DO WHATSAPP SERVICE
info "Copiando código do WhatsApp Service..."
cp -r ./whatsapp-service/* "$INSTALL_DIR/"
chown -R "$MULTIMAX_USER:$MULTIMAX_USER" "$INSTALL_DIR"
success "Código copiado"

# 7. INSTALAR DEPENDÊNCIAS NPM
info "Instalando dependências Node.js..."
cd "$INSTALL_DIR"
sudo -u "$MULTIMAX_USER" npm install --production --silent
success "Dependências instaladas"

# 8. CRIAR PASTA DE AUTENTICAÇÃO
info "Criando diretório de autenticação..."
mkdir -p "$INSTALL_DIR/auth"
chown "$MULTIMAX_USER:$MULTIMAX_USER" "$INSTALL_DIR/auth"
chmod 700 "$INSTALL_DIR/auth"
success "Diretório auth criado"

# 9. CRIAR SERVIÇO SYSTEMD
info "Criando serviço systemd..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=WhatsApp Service for MultiMax (Baileys)
Documentation=https://github.com/SrLuther/MultiMax
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$MULTIMAX_USER
Group=$MULTIMAX_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/node index.js
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Limites de recursos
LimitNOFILE=65536
MemoryLimit=512M

# Segurança
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/auth

[Install]
WantedBy=multi-user.target
EOF
success "Serviço systemd criado"

# 10. CONFIGURAR NGINX
info "Configurando Nginx..."

NGINX_CONF="/etc/nginx/sites-available/multimax"

cat > "$NGINX_CONF" << 'EOF'
# Redirecionar HTTP para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name www.multimax.tec.br multimax.tec.br;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirecionar tudo para HTTPS
    location / {
        return 301 https://www.multimax.tec.br$request_uri;
    }
}

# Configuração HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.multimax.tec.br multimax.tec.br;

    # Certificados SSL (gerenciados pelo Certbot)
    # Descomente após configurar SSL:
    # ssl_certificate /etc/letsencrypt/live/www.multimax.tec.br/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/www.multimax.tec.br/privkey.pem;
    # include /etc/letsencrypt/options-ssl-nginx.conf;
    # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Certificado autoassinado temporário (remover após Certbot)
    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/multimax_access.log;
    error_log /var/log/nginx/multimax_error.log;

    # WhatsApp Service endpoint
    location /notify {
        proxy_pass http://127.0.0.1:3001/notify;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;

        client_max_body_size 10M;
    }

    # MultiMax Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        client_max_body_size 50M;
    }
}
EOF

success "Configuração do Nginx criada"

# Ativar site Nginx
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/multimax
rm -f /etc/nginx/sites-enabled/default

# Testar configuração Nginx
info "Testando configuração do Nginx..."
if nginx -t 2>&1; then
    success "Configuração do Nginx válida"
else
    error "Configuração do Nginx inválida"
    exit 1
fi

# Recarregar Nginx
systemctl reload nginx
success "Nginx recarregado"

# 11. INICIAR SERVIÇO WHATSAPP
info "Habilitando e iniciando serviço WhatsApp..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Aguardar inicialização
sleep 3

# Verificar status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    success "Serviço WhatsApp iniciado com sucesso"
else
    error "Falha ao iniciar serviço WhatsApp"
    error "Ver logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# 12. VALIDAR INSTALAÇÃO
echo ""
info "Executando testes de validação..."

# Teste 1: Porta 3001 está escutando?
if netstat -tuln | grep -q ":3001 "; then
    success "Porta 3001 escutando"
else
    warning "Porta 3001 não está escutando"
fi

# Teste 2: Endpoint local responde?
sleep 2  # Dar tempo para o serviço inicializar completamente
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3001/notify \
    -H "Content-Type: application/json" \
    -d '{"mensagem":"Teste automático"}' || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    success "Endpoint /notify respondendo (HTTP $HTTP_CODE)"
elif [[ "$HTTP_CODE" == "500" ]]; then
    warning "Endpoint respondendo mas com erro interno (HTTP 500)"
    warning "Provavelmente WhatsApp não está autenticado ainda"
else
    warning "Endpoint não respondeu corretamente (HTTP $HTTP_CODE)"
fi

# 13. MENSAGENS FINAIS
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            INSTALAÇÃO CONCLUÍDA COM SUCESSO          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}PRÓXIMOS PASSOS:${NC}"
echo ""
echo "1. ${YELLOW}AUTENTICAR WHATSAPP:${NC}"
echo "   Visualizar QR Code nos logs:"
echo "   ${GREEN}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo ""
echo "   Escanear QR Code com WhatsApp no celular:"
echo "   WhatsApp > Configurações > Aparelhos conectados > Conectar dispositivo"
echo ""

echo "2. ${YELLOW}CRIAR GRUPO 'Notify':${NC}"
echo "   No WhatsApp, criar um grupo chamado 'Notify'"
echo "   Adicionar ao menos 1 contato além de você"
echo ""

echo "3. ${YELLOW}CONFIGURAR SSL/HTTPS (OBRIGATÓRIO):${NC}"
echo "   ${GREEN}sudo apt install certbot python3-certbot-nginx${NC}"
echo "   ${GREEN}sudo certbot --nginx -d $DOMAIN -d multimax.tec.br${NC}"
echo ""
echo "   Depois, editar /etc/nginx/sites-available/multimax:"
echo "   - Descomentar linhas de certificado SSL"
echo "   - Remover certificado temporário"
echo "   - Recarregar: ${GREEN}sudo systemctl reload nginx${NC}"
echo ""

echo "4. ${YELLOW}TESTAR ENDPOINT PÚBLICO:${NC}"
echo "   ${GREEN}curl -X POST https://$DOMAIN/notify \\${NC}"
echo "   ${GREEN}  -H 'Content-Type: application/json' \\${NC}"
echo "   ${GREEN}  -d '{\"mensagem\":\"Teste público\"}'${NC}"
echo ""

echo "5. ${YELLOW}CONFIGURAR MULTIMAX:${NC}"
echo "   No arquivo .env do MultiMax (container):"
echo "   ${GREEN}WHATSAPP_NOTIFY_URL=https://$DOMAIN/notify${NC}"
echo ""

echo -e "${BLUE}COMANDOS ÚTEIS:${NC}"
echo "  • Status:  ${GREEN}sudo systemctl status $SERVICE_NAME${NC}"
echo "  • Logs:    ${GREEN}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo "  • Restart: ${GREEN}sudo systemctl restart $SERVICE_NAME${NC}"
echo "  • Stop:    ${GREEN}sudo systemctl stop $SERVICE_NAME${NC}"
echo ""

echo -e "${BLUE}DOCUMENTAÇÃO COMPLETA:${NC}"
echo "  ${GREEN}docs/infra-whatsapp.md${NC}"
echo ""

warning "IMPORTANTE: Configure SSL antes de usar em produção!"
echo ""
