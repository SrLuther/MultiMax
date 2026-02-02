# 📱 Central de Notificações e Observabilidade MultiMax

## O que é?

A **Central de Notificações** transforma o serviço WhatsApp do MultiMax em um sistema de observabilidade em tempo real. Qualquer evento crítico do aplicativo é capturado e enviado automaticamente para seu telefone via WhatsApp.

## O que é monitorado?

### 1. **Erros e Exceções** ❌
- Exceções não tratadas (uncaught exceptions)
- Promises rejeitadas (unhandled rejections)
- Erros 5xx do API
- Stack traces completos (truncados a 1300 caracteres)

### 2. **Eventos Docker** 🐳
- Container iniciado/parado/reiniciado
- Container morreu inesperadamente
- Útil para detectar restarts em loop

### 3. **Heartbeat** 💚
- Sinal de vida a cada 6 horas
- Confirma que o sistema está online
- Automático, sem configuração

### 4. **Startup** 🚀
- Notificação quando MultiMax inicia
- Mostra PID e NODE_ENV
- Útil para rastrear deployments

### 5. **Testes** 🧪
- Endpoint manual para testar conectividade
- Valida que o número está configurado corretamente

## Como usar?

### 1️⃣ Configurar número de alerta

O número deve estar salvo no banco de dados na tabela `system_settings`.

**Via Dashboard (em desenvolvimento):**
- Ir em Configurações → Central de Notificações
- Clicar em "Alterar Número"
- Inserir número: `11987654321` ou `+5511987654321`
- Clicar em "Salvar"

**Via API (curl):**
```bash
curl -X PUT http://localhost:3001/settings/alert-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "11987654321"}'
```

**Formato aceito:**
- ✅ `11987654321` (apenas dígitos, com DDD)
- ✅ `+5511987654321` (com código do país)
- ✅ `(11) 98765-4321` (com pontuação)
- ❌ `1198765-4321` (sem DDD)
- ❌ `9876543210` (sem DDD)

**Resposta:**
```json
{
  "sucesso": true,
  "phone": "5511987654321@s.whatsapp.net",
  "message": "Número de alerta atualizado com sucesso"
}
```

### 2️⃣ Testar a configuração

**Via API (curl):**
```bash
curl -X POST http://localhost:3001/settings/test-alert-phone
```

**Resposta (sucesso):**
```json
{
  "sucesso": true,
  "message": "Teste enviado com sucesso"
}
```

Você deve receber uma mensagem no WhatsApp em segundos:
```
🧪 Teste da Central de Notificações MultiMax
Este é um teste de conectividade do sistema de alertas

Detalhes:
├ Fonte: whatsapp-service
├ Contexto: test_alert
├ Host: prod-server
├ Hora: 14:23:45 15/01
└ Stack: (sem erro)

🔗 Abrir em: http://localhost:5000/observabilidade?event=test_alert
```

### 3️⃣ Monitorar eventos

Qualquer evento será entregue automaticamente no WhatsApp configurado.

**Exemplo de erro:**
```
❌ Exception não tratada no processo Node.js
ReferenceError: cannot read property 'foo' of undefined

Detalhes:
├ Fonte: system
├ Contexto: unhandled_exception
├ Stack (truncado):
  Error: ReferenceError: cannot read property 'foo' of undefined
    at middleware.js:45:20
    at processRequest [as handle] (internal/http:4020:45)
```

## Endpoints disponíveis

### Health Check
```bash
GET /health
# Retorna: { status: "ok", whatsapp_connected: true, ... }

GET /health/whatsapp
# Retorna: { connected: true, timestamp: "..." }
```

### Configuração
```bash
GET /settings/alert-phone
# Busca número atual configurado

PUT /settings/alert-phone
# Atualiza número (requer JSON body com campo "phone")

POST /settings/test-alert-phone
# Envia mensagem de teste
```

### Testes
```bash
POST /test-error-log
# Gera erro proposital para testar sistema
```

## Estrutura de eventos

Cada evento tem a seguinte estrutura:

```javascript
{
  type: "error"|"warning"|"info"|"startup"|"heartbeat"|"docker"|"test",
  level: "info"|"warn"|"error"|"fatal",
  source: "api"|"frontend"|"system"|"whatsapp-service"|"docker",
  description: "Descrição humanizada",
  message: "Mensagem técnica do erro",
  stack: "(opcional) Stack trace",
  context: "identificador único do evento",
  route: "(opcional) /api/endpoint",
  host: "hostname do servidor",
  timestamp: "ISO 8601 timestamp",
  user: "(opcional) usuário que causou erro"
}
```

## Anti-spam

O sistema implementa anti-spam via **hash MD5**:

- Eventos idênticos dentro de **5 minutos** são ignorados
- Previne flooding de alertas para o mesmo erro repetido
- Cada tipo/source/mensagem é considerada única
- TTL: 5 minutos (configurável)

## Heartbeat automático

- ✅ Enviado **automaticamente a cada 6 horas**
- ✅ Primeira mensagem após 10 segundos do startup
- ✅ Confirma que sistema está operacional
- ✅ Sem necessidade de configuração

**Exemplo:**
```
💚 MultiMax online e operacional
Health check periódico

Detalhes:
├ Fonte: whatsapp-service
├ Contexto: heartbeat
├ Host: prod-server
├ Hora: 14:23:45 15/01
```

## Integração com o código

### Enviar evento customizado

```javascript
const { sendEvent } = require('./whatsapp-service/errorWhatsapp');
const sock = require('./whatsapp-service').globalSocket;
const db = require('./database').pool;

await sendEvent(sock, {
  type: 'error',
  level: 'error',
  source: 'meu-modulo',
  description: 'Erro ao processar PDF',
  message: err.message,
  stack: err.stack,
  context: 'pdf_generation_v2',
  route: '/api/gerar-pdf',
  host: process.env.HOSTNAME,
  timestamp: new Date().toISOString(),
}, db);
```

### Adicionar global error handler no seu middleware

```javascript
// Em app.py (se for Flask) ou Express
app.use((err, req, res, next) => {
  // ... seu código de erro ...
  
  // Enviar para WhatsApp via endpoint
  fetch('http://localhost:3001/notify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mensagem: `[ERRO] ${err.message}`,
      origin: 'api',
    })
  }).catch(e => console.error('Erro ao enviar alerta:', e));
});
```

## Troubleshooting

### ❌ "Número de alerta não configurado"

**Solução:** Configure o número via API ou dashboard.

```bash
curl -X PUT http://localhost:3001/settings/alert-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "11987654321"}'
```

### ❌ "WhatsApp não está conectado"

**Solução:** Conectar pelo QR code.

1. Verificar logs: `docker logs whatsapp-service`
2. QR code deverá aparecer nos logs
3. Escanear com seu WhatsApp
4. Verificar se `/health/whatsapp` retorna `"connected": true`

### ❌ "Falha ao enviar teste"

**Possíveis causas:**
- Número não configurado (sem @s.whatsapp.net)
- WhatsApp não conectado
- Baileys session expirada (apagar pasta `auth/`)
- Bloquear MultiMax no WhatsApp

### ⏱️ Não recebo heartbeat

**Verificações:**
- WhatsApp deve estar conectado
- Número configurado corretamente
- Ver logs: `docker logs whatsapp-service | grep heartbeat`
- Próximo heartbeat em até 6 horas

## Roadmap futuro

- [ ] Dashboard com histórico de eventos
- [ ] Filtros por tipo/source/level
- [ ] Múltiplos números de alerta
- [ ] Integração com Telegram / Slack
- [ ] Rate limiting personalizável
- [ ] Webhooks customizados

---

**Dúvidas?** Consulte a documentação técnica em `/docs/ALERTAS_WHATSAPP_TECNICO.md`
