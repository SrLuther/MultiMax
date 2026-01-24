param(
    [string]$Token = "MaxWhatsTK@963"
)

$MM_HOST = "157.230.170.248"
$MM_USER = "multimax"
$APP_PATH = "/opt/multimax"

$remoteCommand = @'
cd /opt/multimax
echo "[INFO] cwd=$(pwd)"
echo "[INFO] writing token to .env.txt"
cat > .env.txt <<'EOF'
WHATSAPP_SERVICE_TOKEN=__TOKEN__
EOF
echo "[INFO] cat .env.txt" && head -n 5 .env.txt || true
echo "[STEP] Teste 1 sem Authorization"
CODE1=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -d "message=teste")
echo "[TESTE 1] HTTP $CODE1"
echo "[STEP] Teste 2 com Authorization Bearer"
RESP2=$(curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -H "Authorization: Bearer __TOKEN__" -d "message=teste")
echo "[RAW]"
echo "$RESP2"
'@

$remoteCommand = $remoteCommand -replace "__TOKEN__", $Token
$remoteCommand = $remoteCommand -replace "`r", ""

ssh "$MM_USER@$MM_HOST" "bash -lc '$remoteCommand'"
