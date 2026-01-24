#!/bin/bash

# Script de atualização e deploy da MultiMax VPS com tratamento de erros
# Uso: bash deploy-vps-improved.sh

set -e  # Para na primeira falha

echo "=========================================="
echo "🚀 Iniciando deploy da MultiMax"
echo "=========================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para logging com erro
error_exit() {
    echo -e "${RED}❌ ERRO: $1${NC}"
    exit 1
}

# Função para logging com sucesso
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Função para logging com aviso
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar se está em /opt/multimax
if [ ! -d "/opt/multimax" ]; then
    error_exit "Diretório /opt/multimax não encontrado"
fi

cd /opt/multimax || error_exit "Não foi possível entrar em /opt/multimax"
success "Diretório /opt/multimax encontrado"

# ============================================
# 1. ATUALIZAR REPOSITÓRIO
# ============================================
echo ""
echo "📥 Atualizando repositório..."
git fetch origin || error_exit "Falha ao fazer git fetch"
success "Git fetch completado"

git reset --hard origin/nova-versao-deploy || error_exit "Falha ao fazer git reset"
success "Repositório atualizado para a versão mais recente"

# ============================================
# 2. PARAR CONTAINERS
# ============================================
echo ""
echo "🛑 Parando containers..."
docker-compose down --remove-orphans || warning "docker-compose down encontrou problemas, continuando..."
success "Docker-compose encerrado"

# ============================================
# 3. AGUARDAR ANTES DE REMOVER
# ============================================
echo "⏳ Aguardando 3 segundos para liberar recursos..."
sleep 3

# ============================================
# 4. REMOVER CONTAINERS ANTIGOS
# ============================================
echo ""
echo "🧹 Limpando containers antigos..."
CONTAINERS=$(docker ps -a | grep multimax | awk '{print $1}' | wc -l)
if [ "$CONTAINERS" -gt 0 ]; then
    docker ps -a | grep multimax | awk '{print $1}' | xargs -r docker rm -f
    success "Containers antigos removidos ($CONTAINERS containers)"
else
    success "Nenhum container antigo para remover"
fi

# ============================================
# 5. LIMPEZA DE REDES E VOLUMES
# ============================================
echo ""
echo "🧹 Limpando redes e volumes não utilizados..."
docker network prune -f > /dev/null 2>&1 && success "Redes limpas" || warning "Erro ao limpar redes (não crítico)"
docker volume prune -f > /dev/null 2>&1 && success "Volumes limpos" || warning "Erro ao limpar volumes (não crítico)"
docker image prune -f > /dev/null 2>&1 && success "Imagens limpas" || warning "Erro ao limpar imagens (não crítico)"

# ============================================
# 6. CONSTRUIR IMAGEM
# ============================================
echo ""
echo "🔨 Construindo imagem Docker..."
docker-compose build --no-cache || error_exit "Falha ao construir imagem Docker"
success "Imagem Docker construída com sucesso"

# ============================================
# 7. INICIAR CONTAINER
# ============================================
echo ""
echo "🚀 Iniciando container..."
docker-compose up -d || error_exit "Falha ao iniciar docker-compose"
success "Container iniciado"

# ============================================
# 8. AGUARDAR INICIALIZAÇÃO
# ============================================
echo ""
echo "⏳ Aguardando inicialização do container (15 segundos)..."
sleep 15

# ============================================
# 9. VERIFICAR STATUS
# ============================================
echo ""
echo "📊 Verificando status..."

# Verificar se container está rodando
if docker ps | grep -q multimax; then
    success "Container multimax está rodando"
else
    error_exit "Container multimax não está rodando!"
fi

# Mostrar porta
PORT=$(docker ps | grep multimax | awk '{print $NF}')
success "Container rodando: $PORT"

# Verificar logs
echo ""
echo "📋 Últimas linhas dos logs:"
docker logs multimax --tail 10 | head -20

# ============================================
# SUCESSO FINAL
# ============================================
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Deploy completado com sucesso!${NC}"
echo "=========================================="
echo ""
echo "Aplicação disponível em:"
echo "  http://157.230.170.248:5000"
echo ""
echo "Comandos úteis:"
echo "  Ver logs:          docker logs multimax -f"
echo "  Verificar status:  docker ps"
echo "  Entrar no bash:    docker exec -it multimax bash"
echo ""
