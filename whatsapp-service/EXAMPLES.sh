#!/bin/bash
# whatsapp-service/EXAMPLES.sh
# Exemplos de uso da API - execute os comandos abaixo

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost:3001"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Central de Notificações MultiMax - Exemplos de Uso${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

# ============================================================================
# 1. HEALTHCHECK
# ============================================================================
echo -e "${YELLOW}1. Verificar saúde do serviço${NC}"
echo -e "   ${BLUE}GET /health${NC}\n"
echo "   Comando:"
echo "   curl $BASE_URL/health | jq ."
echo ""
echo "   Esperado:"
echo '   {
     "status": "ok",
     "service": "whatsapp-service",
     "whatsapp_connected": true,
     "timestamp": "2024-01-15T14:23:45.123Z"
   }'
echo ""

# ============================================================================
# 2. WHATSAPP HEALTHCHECK
# ============================================================================
echo -e "${YELLOW}2. Verificar conexão WhatsApp${NC}"
echo -e "   ${BLUE}GET /health/whatsapp${NC}\n"
echo "   Comando:"
echo "   curl $BASE_URL/health/whatsapp | jq ."
echo ""
echo "   Esperado:"
echo '   {
     "connected": true,
     "timestamp": "2024-01-15T14:23:45.123Z"
   }'
echo ""

# ============================================================================
# 3. OBTER NÚMERO CONFIGURADO
# ============================================================================
echo -e "${YELLOW}3. Obter número de alerta configurado${NC}"
echo -e "   ${BLUE}GET /settings/alert-phone${NC}\n"
echo "   Comando:"
echo "   curl $BASE_URL/settings/alert-phone | jq ."
echo ""
echo "   Esperado:"
echo '   {
     "phone": "5511987654321@s.whatsapp.net",
     "configured": true,
     "last_test": null
   }'
echo ""

# ============================================================================
# 4. CONFIGURAR NÚMERO
# ============================================================================
echo -e "${YELLOW}4. Configurar/atualizar número de alerta${NC}"
echo -e "   ${BLUE}PUT /settings/alert-phone${NC}\n"
echo "   Comando:"
echo '   curl -X PUT '"$BASE_URL"'/settings/alert-phone \\'
echo '     -H "Content-Type: application/json" \\'
echo "     -d '{\"phone\": \"11987654321\"}'"
echo ""
echo "   Formatos aceitos:"
echo "   ✓ 11987654321"
echo "   ✓ +5511987654321"
echo "   ✓ (11) 98765-4321"
echo ""
echo "   Esperado:"
echo '   {
     "sucesso": true,
     "phone": "5511987654321@s.whatsapp.net",
     "message": "Número de alerta atualizado com sucesso"
   }'
echo ""

# ============================================================================
# 5. TESTAR ALERTA
# ============================================================================
echo -e "${YELLOW}5. Enviar teste de alerta${NC}"
echo -e "   ${BLUE}POST /settings/test-alert-phone${NC}\n"
echo "   Comando:"
echo "   curl -X POST $BASE_URL/settings/test-alert-phone | jq ."
echo ""
echo "   Esperado:"
echo '   {
     "sucesso": true,
     "message": "Teste enviado com sucesso"
   }'
echo ""
echo "   Você deve receber uma mensagem no WhatsApp:"
echo "   🧪 Teste da Central de Notificações MultiMax"
echo "   Este é um teste de conectividade do sistema de alertas"
echo ""

# ============================================================================
# 6. ENVIAR MENSAGEM PARA GRUPO NOTIFY
# ============================================================================
echo -e "${YELLOW}6. Enviar mensagem para grupo Notify${NC}"
echo -e "   ${BLUE}POST /notify${NC}\n"
echo "   Comando:"
echo '   curl -X POST '"$BASE_URL"'/notify \\'
echo '     -H "Content-Type: application/json" \\'
echo "     -d '{"
echo '       "mensagem": "Relatório diário gerado com sucesso",'
echo '       "origin": "relatorio"'
echo '     }'
echo "   '"
echo ""
echo "   Com arquivo (base64):"
echo '   curl -X POST '"$BASE_URL"'/notify \\'
echo '     -H "Content-Type: application/json" \\'
echo "     -d '{"
echo '       "mensagem": "PDF de relatório em anexo",'
echo '       "arquivo_base64": "JVBERi0xLjQKJeLj...",'
echo '       "nome_arquivo": "relatorio.pdf"'
echo '     }'
echo "   '"
echo ""
echo "   Esperado:"
echo '   {
     "sucesso": true,
     "mensagem": "Enviado para grupo Notify"
   }'
echo ""

# ============================================================================
# 7. GERAR ERRO PROPOSITAL (TESTE)
# ============================================================================
echo -e "${YELLOW}7. Gerar erro proposital para testar alertas${NC}"
echo -e "   ${BLUE}POST /test-error-log${NC}\n"
echo "   Comando:"
echo "   curl -X POST $BASE_URL/test-error-log | jq ."
echo ""
echo "   Esperado:"
echo '   {
     "sucesso": true,
     "message": "Erro de teste enviado para alertas"
   }'
echo ""
echo "   Você deve receber um alerta de erro no WhatsApp:"
echo "   ❌ Erro proposital gerado por teste manual"
echo "   Erro proposital para teste do sistema de alertas"
echo ""

# ============================================================================
# BASH SCRIPT COMPLETO
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
echo -e "${YELLOW}SCRIPT BASH PARA AUTOMAÇÃO${NC}\n"

cat << 'EOF'
#!/bin/bash
# Script para testar todos os endpoints automaticamente

BASE_URL="http://localhost:3001"

echo "🧪 Testando Central de Notificações..."

# 1. Health
echo -n "1. Healthcheck... "
curl -s "$BASE_URL/health" | grep -q "ok" && echo "✓" || echo "✗"

# 2. WhatsApp status
echo -n "2. Status WhatsApp... "
curl -s "$BASE_URL/health/whatsapp" | grep -q "timestamp" && echo "✓" || echo "✗"

# 3. Get current alert phone
echo -n "3. Número configurado... "
curl -s "$BASE_URL/settings/alert-phone" | grep -q "configured" && echo "✓" || echo "✗"

# 4. Set alert phone
echo -n "4. Configurando número... "
RESPONSE=$(curl -s -X PUT "$BASE_URL/settings/alert-phone" \
  -H "Content-Type: application/json" \
  -d '{"phone": "11987654321"}')
echo "$RESPONSE" | grep -q "sucesso" && echo "✓" || echo "✗"

# 5. Test alert
echo -n "5. Enviando teste... "
curl -s -X POST "$BASE_URL/settings/test-alert-phone" | grep -q "sucesso" && echo "✓" || echo "✗"

# 6. Error log
echo -n "6. Testando error handler... "
curl -s -X POST "$BASE_URL/test-error-log" | grep -q "sucesso" && echo "✓" || echo "✗"

# 7. Notify group
echo -n "7. Enviando para grupo... "
RESPONSE=$(curl -s -X POST "$BASE_URL/notify" \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Teste de mensagem", "origin": "test"}')
echo "$RESPONSE" | grep -q "sucesso" && echo "✓" || echo "✗"

echo ""
echo "✅ Testes concluídos!"
EOF

echo ""
echo ""

# ============================================================================
# PYTHON SCRIPT COMPLETO
# ============================================================================
echo -e "${YELLOW}SCRIPT PYTHON PARA AUTOMAÇÃO${NC}\n"

cat << 'EOF'
#!/usr/bin/env python3
"""
Script para testar Central de Notificações via Python
"""

import requests
import json

BASE_URL = "http://localhost:3001"

def test_endpoints():
    tests = [
        ("GET", "/health", None),
        ("GET", "/health/whatsapp", None),
        ("GET", "/settings/alert-phone", None),
        ("PUT", "/settings/alert-phone", {"phone": "11987654321"}),
        ("POST", "/settings/test-alert-phone", None),
        ("POST", "/test-error-log", None),
        ("POST", "/notify", {"mensagem": "Teste", "origin": "test"}),
    ]

    for method, path, data in tests:
        url = f"{BASE_URL}{path}"
        try:
            if method == "GET":
                resp = requests.get(url)
            elif method == "POST":
                resp = requests.post(url, json=data)
            elif method == "PUT":
                resp = requests.put(url, json=data)

            status = "✓" if resp.status_code in [200, 201] else "✗"
            print(f"{status} {method} {path}: {resp.status_code}")

        except Exception as e:
            print(f"✗ {method} {path}: {e}")

if __name__ == "__main__":
    print("🧪 Testando Central de Notificações...\n")
    test_endpoints()
    print("\n✅ Testes concluídos!")
EOF

echo ""
echo ""

# ============================================================================
# POSTMAN COLLECTION
# ============================================================================
echo -e "${YELLOW}POSTMAN COLLECTION (JSON)${NC}\n"

cat << 'EOF'
{
  "info": {
    "name": "Central de Notificações MultiMax",
    "description": "Collection com todos os endpoints",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:3001/health",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3001",
          "path": ["health"]
        }
      }
    },
    {
      "name": "Get Alert Phone",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:3001/settings/alert-phone",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3001",
          "path": ["settings", "alert-phone"]
        }
      }
    },
    {
      "name": "Set Alert Phone",
      "request": {
        "method": "PUT",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"phone\": \"11987654321\"}"
        },
        "url": {
          "raw": "http://localhost:3001/settings/alert-phone",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3001",
          "path": ["settings", "alert-phone"]
        }
      }
    },
    {
      "name": "Test Alert",
      "request": {
        "method": "POST",
        "url": {
          "raw": "http://localhost:3001/settings/test-alert-phone",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3001",
          "path": ["settings", "test-alert-phone"]
        }
      }
    },
    {
      "name": "Send to Notify Group",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"mensagem\": \"Teste de mensagem\", \"origin\": \"test\"}"
        },
        "url": {
          "raw": "http://localhost:3001/notify",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3001",
          "path": ["notify"]
        }
      }
    }
  ]
}
EOF

echo ""
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Para usar os scripts acima, copie e execute no terminal:${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"
