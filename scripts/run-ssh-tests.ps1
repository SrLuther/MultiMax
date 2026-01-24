param(
    [string]$Token = "MaxWhatsTK@963"
)

$MM_HOST = "157.230.170.248"
$MM_USER = "multimax"
$APP_PATH = "/opt/multimax"

$remoteCommand = @'
cd /opt/multimax
CODE1=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -d "message=teste")
echo "[TESTE 1] Sem Authorization -> HTTP $CODE1"
printf "WHATSAPP_SERVICE_TOKEN=%s\n" "__TOKEN__" > .env.txt
RESP2=$(curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -H "Authorization: Bearer __TOKEN__" -d "message=teste")
echo "$RESP2"
'@
$remoteCommand = @'
cd /opt/multimax
CODE1=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -d "message=teste")
echo "[TESTE 1] Sem Authorization -> HTTP $CODE1"
printf "WHATSAPP_SERVICE_TOKEN=%s\n" "__TOKEN__" > .env.txt
RESP2=$(curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:5000/dev/whatsapp/enviar -H "Authorization: Bearer __TOKEN__" -d "message=teste")
echo "$RESP2"
'@

$remoteCommand = $remoteCommand -replace "__TOKEN__", $Token
$remoteCommand = $remoteCommand -replace "`r", ""

ssh "$MM_USER@$MM_HOST" "bash -lc '$remoteCommand'"
