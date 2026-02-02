#!/bin/bash
# whatsapp-service/QUICKSTART.sh
# Script rápido para testar a Central de Notificações

set -e

echo "🚀 Central de Notificações MultiMax - QuickStart"
echo "=================================================="

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar prerequisites
echo -e "\n${YELLOW}[1/6]${NC} Verificando pré-requisitos..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js não encontrado. Instale Node.js 18+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js encontrado ($(node -v))${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker não encontrado${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker encontrado${NC}"

if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠ psql não encontrado (será necessário para DB)${NC}"
else
    echo -e "${GREEN}✓ psql encontrado${NC}"
fi

# 2. Instalar dependências Node
echo -e "\n${YELLOW}[2/6]${NC} Instalando dependências Node..."
cd "$(dirname "$0")" || exit
npm install
echo -e "${GREEN}✓ Dependências instaladas${NC}"

# 3. Criar tabela de configuração
echo -e "\n${YELLOW}[3/6]${NC} Criando schema de banco de dados..."
if [ -f schema.sql ]; then
    if command -v psql &> /dev/null; then
        # Tentar executar schema
        if psql -U multimax -d multimax -f schema.sql 2>/dev/null; then
            echo -e "${GREEN}✓ Schema criado com sucesso${NC}"
        else
            echo -e "${YELLOW}⚠ Não foi possível conectar ao banco. Execute manualmente:${NC}"
            echo -e "${YELLOW}  psql -U multimax -d multimax -f schema.sql${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ psql não disponível. Execute schema.sql manualmente:${NC}"
        echo -e "${YELLOW}  psql -U multimax -d multimax -f schema.sql${NC}"
    fi
else
    echo -e "${YELLOW}⚠ schema.sql não encontrado${NC}"
fi

# 4. Testar conexão local
echo -e "\n${YELLOW}[4/6]${NC} Iniciando serviço em modo teste..."
echo -e "${YELLOW}Pressione Ctrl+C após ver a conexão com WhatsApp...${NC}\n"

# Timeout de 30 segundos
timeout 30s node index.js || true

# 5. Testar endpoints
echo -e "\n${YELLOW}[5/6]${NC} Testando endpoints HTTP..."
sleep 2

if curl -s http://localhost:3001/health > /dev/null; then
    echo -e "${GREEN}✓ Endpoint /health respondendo${NC}"
else
    echo -e "${RED}✗ Endpoint /health não respondendo${NC}"
fi

# 6. Instruções finais
echo -e "\n${YELLOW}[6/6]${NC} Próximos passos"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "1. Configurar número de WhatsApp:"
echo -e "   ${YELLOW}curl -X PUT http://localhost:3001/settings/alert-phone \\${NC}"
echo -e "   ${YELLOW}-d '{\"phone\": \"11987654321\"}'${NC}"
echo ""
echo "2. Testar envio:"
echo -e "   ${YELLOW}curl -X POST http://localhost:3001/settings/test-alert-phone${NC}"
echo ""
echo "3. Ver documentação:"
echo -e "   ${YELLOW}cat ALERTAS_WHATSAPP.md${NC}"
echo ""
echo "4. Deployment em Docker:"
echo -e "   ${YELLOW}cat DEPLOYMENT.md${NC}"
echo ""
echo -e "${GREEN}✓ Setup concluído!${NC}"
