#!/usr/bin/env bash
set -euo pipefail

TOKEN=${1:-}
if [[ -z "$TOKEN" ]]; then
  echo "[ERRO] Token não fornecido" >&2
  exit 1
fi

cd /opt/multimax
CODE1=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -d 'message=teste')
echo "[TESTE 1] Sem Authorization -> HTTP $CODE1"
printf 'WHATSAPP_SERVICE_TOKEN=%s\n' "$TOKEN" | sudo tee .env.txt >/dev/null
RESP2=$(curl -s -w '\nHTTP_STATUS:%{http_code}\n' -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -H "Authorization: Bearer $TOKEN" -d 'message=teste')
echo "$RESP2"
