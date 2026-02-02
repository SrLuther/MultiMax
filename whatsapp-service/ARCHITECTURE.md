"""
Central de Notificações MultiMax - Diagrama da Arquitetura

SISTEMA COMPLETO:

                           ┌─────────────────────────┐
                           │    MultiMax API         │
                           │    (Python/Flask)       │
                           └────────────┬────────────┘
                                        │
                                        │ HTTP
                                        │ POST /notify
                                        │
                    ┌───────────────────▼────────────────────┐
                    │                                         │
                    │   CENTRAL DE NOTIFICAÇÕES               │
                    │   whatsapp-service (Node.js 20)         │
                    │                                         │
                    │  ┌─────────────────────────────────┐  │
                    │  │  index.js (543 linhas)          │  │
                    │  │  - HTTP Server (port 3001)      │  │
                    │  │  - Baileys Socket               │  │
                    │  │  - Exception Handlers           │  │
                    │  │  - Heartbeat (6h)               │  │
                    │  │  - Docker Listener init         │  │
                    │  │  - 7 Endpoints                  │  │
                    │  └─────────────────────────────────┘  │
                    │                                         │
                    │  ┌─────────────────────────────────┐  │
                    │  │  errorWhatsapp.js (350+ linhas) │  │
                    │  │  - sendEvent()                  │  │
                    │  │  - Anti-spam (MD5 hash)         │  │
                    │  │  - Phone validation             │  │
                    │  │  - Message formatting           │  │
                    │  │  - DB queries                   │  │
                    │  └─────────────────────────────────┘  │
                    │                                         │
                    │  ┌─────────────────────────────────┐  │
                    │  │  dockerListener.js (140 linhas) │  │
                    │  │  - docker events spawn          │  │
                    │  │  - Container filtering          │  │
                    │  │  - Auto-reconnect               │  │
                    │  │  - sendEvent integration        │  │
                    │  └─────────────────────────────────┘  │
                    │                                         │
                    └───────────────┬────────────┬───────────┘
                                    │            │
                                    │            │
                    HTTP POST        │            │      SOCKET
                    /settings/*      │            │      docker.sock
                                    │            │
                        ┌───────────▼─┐      ┌────▼──────────┐
                        │  PostgreSQL │      │  Docker       │
                        │  system_    │      │  Daemon       │
                        │  settings   │      │               │
                        │             │      │  container    │
                        │ alert_phone │      │  events:      │
                        │ last_test   │      │  start/stop   │
                        └─────────────┘      │  restart/die  │
                                             └────┬──────────┘
                                                  │
                        ┌─────────────────────────┘
                        │
                        │ Monitoring
                        │ Real-time
                        │
                        ▼
              ┌─────────────────────┐
              │  WhatsApp Cloud     │
              │  (Baileys)          │
              │                     │
              │  📱 Seu Telefone    │
              │  +55 11 98765-4321  │
              └─────────────────────┘


FLUXO DE EVENTOS:

1. ERRO OCORRE
   └─> API Flask / Node Exception
       └─> Exception Handler
           └─> sendEvent()
               └─> POST /notify ou HTTP direto
                   └─> index.js /notify endpoint
                       └─> errorWhatsapp.sendEvent()
                           ├─> Hash MD5 (anti-spam)
                           ├─> Query system_settings (número)
                           ├─> Validar/formatar telefone
                           ├─> Formatar mensagem WhatsApp
                           └─> Baileys.sendMessage()
                               └─> ✅ Mensagem no seu telefone


2. DOCKER EVENT
   └─> Docker Daemon
       └─> "docker events --format {{json .}}"
           └─> dockerListener subprocess
               └─> Filtrar (start/stop/restart/die)
                   └─> sendEvent()
                       └─> errorWhatsapp.sendEvent()
                           └─> ✅ Alerta no seu telefone


3. HEARTBEAT (AUTOMÁTICO)
   └─> index.js setInterval (6 horas)
       └─> sendHeartbeat()
           └─> sendEvent() com type='heartbeat'
               └─> ✅ "💚 MultiMax online" no seu telefone


4. TESTE MANUAL
   └─> curl POST /settings/test-alert-phone
       └─> sendEvent() com type='test'
           └─> ✅ "🧪 Teste da Central" no seu telefone


ENDPOINTS DISPONÍVEIS:

GET  /health                          → Status geral do serviço
GET  /health/whatsapp                 → Status WhatsApp
POST /notify                          → Enviar para grupo Notify
GET  /settings/alert-phone            → Obter número configurado
PUT  /settings/alert-phone            → Atualizar número
POST /settings/test-alert-phone       → Enviar teste
POST /test-error-log                  → Gerar erro proposital


TIPOS DE EVENTOS:

Event Type     │ Level │ Emoji │ Quando Ocorre
───────────────┼───────┼───────┼──────────────────────────────
startup        │ info  │ 🚀    │ MultiMax inicia
heartbeat      │ info  │ 💚    │ A cada 6 horas
error          │ error │ ❌    │ Exceção não tratada
fatal          │ fatal │ 🔴    │ Erro crítico
docker         │ warn  │ 🐳    │ Container stop/die
test           │ info  │ 🧪    │ Teste manual
warning        │ warn  │ ⚠️    │ Aviso genérico


DADOS PERSISTENTES:

PostgreSQL (system_settings table):
┌─────────────────────────────────────┐
│ key                                 │ value
├─────────────────────────────────────┤
│ alert_whatsapp_phone                │ 5511987654321@s.whatsapp.net
│ last_test_alert_at                  │ 2024-01-15T14:23:45Z
└─────────────────────────────────────┘

Arquivo (whatsapp-service/auth/):
├── creds.json              ← Credenciais Baileys encriptadas
├── session-multimax.json   ← Session data
└── pre-key-*.json          ← Pre-keys para criptografia


EXEMPLO DE MENSAGEM:

❌ Exception não tratada no processo Node.js
ReferenceError: cannot read property 'foo' of undefined

Detalhes:
├ Fonte: system
├ Contexto: unhandled_exception
├ Host: prod-server
├ Hora: 14:23:45 15/01
├ Usuário: admin@multimax.com
└ Stack (truncado):
  Error: ReferenceError: cannot read property 'foo'
    at middleware.js:45:20
    at processRequest [as handle]
    at Layer.handle [as handle_request]
    at next (internal/http:5050:45)
    at async getUser (auth.js:120:15)

🔗 Abrir em: http://localhost:5000/observabilidade?event=unhandled_exception


ANTI-SPAM LOGIC:

Evento 1 (14:00) → Hash: abc123 → Enviado ✓
                  Cache: {abc123: {lastSent: 14:00}}

Evento 2 (14:02) → Hash: abc123 → Ignorado ⏭️
                  (ainda dentro do TTL de 5 min)

Evento 3 (14:06) → Hash: abc123 → Enviado ✓
                  (passou do TTL, cache limpo)


DEPLOYMENT OVERVIEW:

┌──────────────────────────────────────────────────────────────┐
│                      Docker Host                              │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Container: multimax-whatsapp                          │   │
│  │  Image: node:20-alpine                                │   │
│  │  Port: 3001:3001                                      │   │
│  │  PID: 1 (node index.js)                               │   │
│  │                                                        │   │
│  │  Volumes:                                              │   │
│  │  - /var/run/docker.sock (docker events)               │   │
│  │  - ./whatsapp-service/auth (credentials persist)      │   │
│  │                                                        │   │
│  │  Environment:                                          │   │
│  │  - NODE_ENV=production                                │   │
│  │  - HOSTNAME=prod-server                               │   │
│  │  - APP_BASE_URL=http://localhost:5000                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  Resources:                                                    │
│  - RAM: 150-200MB                                              │
│  - CPU: <1% idle                                               │
│  - Network: 1 WebSocket (Baileys)                             │
│  - Storage: ~50MB (node_modules, auth, logs)                  │
└──────────────────────────────────────────────────────────────┘


SECURITY ARCHITECTURE:

┌─────────────────┐
│ Frontend/API    │  ← HTTP requests
└────────┬────────┘
         │
    POST /notify (pode ser publico)
         │
    ┌────▼────────────────────────────┐
    │ index.js                        │
    │ - Valida request                │
    │ - Chama sendEvent()             │
    └────┬─────────────────────────────┘
         │
    ┌────▼────────────────────────────┐
    │ errorWhatsapp.js                │
    │ - Valida telefone (regex)       │
    │ - Valida hash (anti-spam)       │
    │ - Busca numero no DB            │
    └────┬─────────────────────────────┘
         │
    ┌────▼────────────────────────────┐
    │ Baileys Socket                  │
    │ - TLS encryption                │
    │ - WhatsApp protocol             │
    └────┬─────────────────────────────┘
         │
    ┌────▼────────────────────────────┐
    │ Seu Telefone                    │
    │ (WhatsApp app)                  │
    └─────────────────────────────────┘

⚠️ Endpoints /settings/* devem ser protegidos com autenticação
✓ Socket Docker em read-only
✓ Credenciais em volume persistente (não em ENV)


PERFORMANCE CONSIDERATIONS:

- Operações síncronas (getAlertPhone): ~50ms
- Operações de rede (sendMessage): ~1-3s
- Anti-spam check: <1ms (hash lookup)
- Docker events: assincrono (stream contínuo)
- Heartbeat: background interval (não bloqueia)

Recomendações:
- Max 100 eventos/hora antes de rate limiting
- TTL anti-spam: 5 minutos
- Heartbeat: 6 horas (configurável)
- DB pool size: 5-10 conexões
- Timeout de HTTP: 30 segundos


LOGGING STRUCTURE:

[14:23:45.123] INFO  (whatsapp-service):
  ✓ Alerta enviado: error (unhandled_exception)

[14:23:46.456] WARN  (whatsapp-service):
  ⚠ Número de alerta não configurado

[14:23:47.789] ERROR (whatsapp-service):
  ❌ Erro ao enviar evento: ECONNREFUSED
"""
