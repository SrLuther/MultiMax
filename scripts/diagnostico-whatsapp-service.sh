#!/usr/bin/env bash
set -euo pipefail

# Diagnóstico do endpoint de serviço WhatsApp via token
# Ambiente: executar no VPS onde o Flask está rodando (localhost)
# Uso: ./scripts/diagnostico-whatsapp-service.sh "SEU_TOKEN" "mensagem de teste"

TOKEN_INPUT=${1:-}
MESSAGE=${2:-"teste multimax"}
BASE_URL=${BASE_URL:-"http://127.0.0.1:5000"}
ENDPOINT="$BASE_URL/dev/whatsapp/enviar"

# Função para ler token de .env.txt (fallback)
read_token_from_env_file() {
  local env_file
  # Assume .env.txt na raiz do app (um nível acima de current_app.root_path)
  if [[ -f ".env.txt" ]]; then
    env_file=".env.txt"
  elif [[ -f "$(pwd)/.env.txt" ]]; then
    env_file="$(pwd)/.env.txt"
  else
    env_file=".env.txt"
  fi
  if [[ -f "$env_file" ]]; then
    awk -F '=' '/^WHATSAPP_SERVICE_TOKEN=/ {print $2}' "$env_file" | tr -d '\r' | tr -d ' ' || true
  fi
}

TOKEN=${TOKEN_INPUT}
if [[ -z "$TOKEN" ]]; then
  TOKEN=$(read_token_from_env_file || true)
fi

if [[ -z "$TOKEN" ]]; then
  echo "[ERRO] Token não informado e não encontrado em .env.txt"
  echo "       Passe como primeiro argumento ou crie linha WHATSAPP_SERVICE_TOKEN=... em .env.txt"
  exit 1
fi

echo "[INFO] Testando endpoint: $ENDPOINT"

# Teste 1: sem Authorization (espera 302 redirect para /login)
code1=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$ENDPOINT" -d "message=$MESSAGE") || true
echo "[TESTE 1] Sem Authorization -> HTTP $code1 (esperado 302)"

# Teste 2: com Authorization Bearer
echo "[TESTE 2] Com Authorization: Bearer *****"
resp2=$(curl -s -w '\nHTTP_STATUS:%{http_code}\n' -X POST "$ENDPOINT" -H "Authorization: Bearer $TOKEN" -d "message=$MESSAGE")
http2=$(echo "$resp2" | awk -F ':' '/HTTP_STATUS/ {print $2}')
json2=$(echo "$resp2" | sed '/HTTP_STATUS/d')

echo "[RESULTADO] HTTP $http2"
if [[ "$http2" == "200" ]]; then
  echo "[OK] Resposta JSON: $json2"
else
  echo "[ERRO] Resposta JSON: $json2"
fi

# Sugestão: se 502, verificar logs do serviço WhatsApp e conectividade.
