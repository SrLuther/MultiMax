#!/bin/bash

# Script de teste do WhatsApp Gateway na VPS
# Execute este script na VPS após fazer o deploy das alterações

set -e

echo "=========================================="
echo "🧪 Testando WhatsApp Gateway na VPS"
echo "=========================================="

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funções de logging
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Navegar para diretório do projeto
cd /opt/multimax || { error "Diretório /opt/multimax não encontrado"; exit 1; }

echo ""
info "1. Atualizando código do repositório..."
git fetch origin
git pull origin nova-versao-deploy
success "Código atualizado"

echo ""
info "2. Verificando containers em execução..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
info "3. Reconstruindo container multimax..."
docker-compose build multimax
success "Container reconstruído"

echo ""
info "4. Reiniciando serviços..."
docker-compose up -d
sleep 5
success "Serviços reiniciados"

echo ""
info "5. Verificando status dos containers..."
docker-compose ps

echo ""
info "6. Verificando se whatsapp-service está rodando..."
WHATSAPP_CID=$(docker-compose ps -q whatsapp-service || true)
if [ -z "$WHATSAPP_CID" ]; then
    error "whatsapp-service não encontrado via docker-compose"
else
    WHATSAPP_STATUS=$(docker inspect -f '{{.State.Status}}' "$WHATSAPP_CID" 2>/dev/null || echo "not found")
    if [ "$WHATSAPP_STATUS" = "running" ]; then
        success "whatsapp-service está rodando"
    else
        error "whatsapp-service não está rodando (status: $WHATSAPP_STATUS)"
    fi
fi

echo ""
info "7. Verificando conectividade de rede entre containers..."
if docker-compose exec multimax getent hosts whatsapp-service >/dev/null 2>&1; then
    success "Resolução de nome para whatsapp-service OK"
else
    warning "Falha ao resolver whatsapp-service a partir do multimax"
fi

echo ""
info "8. Verificando logs do whatsapp-service (últimas 20 linhas)..."
echo "----------------------------------------"
docker-compose logs --tail 20 whatsapp-service || true
echo "----------------------------------------"

echo ""
info "9. Verificando logs do multimax (últimas 20 linhas)..."
echo "----------------------------------------"
docker-compose logs --tail 20 multimax || true
echo "----------------------------------------"

echo ""
info "10. Testando endpoint /health do whatsapp-service (interno)..."
HEALTH_RESPONSE=$(docker-compose exec whatsapp-service sh -c "apk add --no-cache curl >/dev/null && curl -s http://localhost:3001/health" 2>/dev/null || echo "error")
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    success "Endpoint /health respondeu: $HEALTH_RESPONSE"
else
    error "Endpoint /health falhou: $HEALTH_RESPONSE"
fi

echo ""
info "11. Verificando variável WHATSAPP_NOTIFY_URL..."
NOTIFY_URL=$(docker exec multimax printenv WHATSAPP_NOTIFY_URL 2>/dev/null || echo "não definida")
echo "   WHATSAPP_NOTIFY_URL = $NOTIFY_URL"
if [ "$NOTIFY_URL" = "http://whatsapp-service:3001/notify" ]; then
    success "URL configurada corretamente"
else
    warning "URL não está como esperado"
fi

echo ""
info "12. Verificando arquivo /.dockerenv no container multimax..."
if docker exec multimax test -f /.dockerenv; then
    success "Container está em ambiente Docker (fallbacks locais desabilitados)"
else
    warning "Arquivo /.dockerenv não encontrado"
fi

echo ""
info "13. Testando endpoint de WhatsApp via Flask..."
echo "   Tentando enviar mensagem de teste via API interna..."

# Ler o token do ambiente
TOKEN=$(docker exec multimax printenv WHATSAPP_SERVICE_TOKEN 2>/dev/null || echo "")
if [ -z "$TOKEN" ]; then
    warning "WHATSAPP_SERVICE_TOKEN não definido"
else
    info "Token encontrado: ${TOKEN:0:10}..."
fi

# Teste interno (dentro do container multimax)
TEST_RESPONSE=$(docker-compose exec multimax sh -lc "apt-get update >/dev/null && apt-get install -y curl >/dev/null && curl -s -X POST \\
    -H 'Authorization: Bearer $TOKEN' \\
    -H 'Content-Type: application/x-www-form-urlencoded' \\
    -d 'message=[TESTE VPS] Gateway funcionando apos correcao de fallbacks Docker' \\
    http://localhost:5000/dev/whatsapp/enviar" 2>/dev/null || echo "error")

echo "   Resposta: $TEST_RESPONSE"

if echo "$TEST_RESPONSE" | grep -q '"ok".*true'; then
    success "Mensagem enviada com sucesso!"
elif echo "$TEST_RESPONSE" | grep -q "token"; then
    error "Erro de autenticação (token inválido ou ausente)"
elif echo "$TEST_RESPONSE" | grep -q "Falha ao contatar"; then
    error "Falha ao contatar serviço WhatsApp - verificar conectividade"
else
    warning "Resposta inesperada do endpoint"
fi

echo ""
echo "=========================================="
success "Testes concluídos!"
echo "=========================================="
echo ""
echo "📋 Resumo:"
echo "   - Se o teste 10 (health check) passou: whatsapp-service está acessível"
echo "   - Se o teste 13 passou: integração completa funcionando"
echo "   - Se teste 13 falhou com 'Falha ao contatar': problema de conectividade ou whatsapp-service inativo"
echo ""
echo "🔍 Para mais detalhes:"
echo "   docker-compose logs -f multimax"
echo "   docker-compose logs -f whatsapp-service"
echo ""
