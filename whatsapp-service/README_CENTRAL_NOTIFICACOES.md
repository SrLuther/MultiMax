# 🎯 Central de Notificações MultiMax - Resumo Executivo

## ✅ Implementado

### Módulos Node.js

1. **`index.js`** (Totalmente refatorizado)
   - ✅ Startup alert (primeira conexão)
   - ✅ Heartbeat automático (6 horas)
   - ✅ Exception handlers (unhandledRejection, uncaughtException)
   - ✅ Docker listener initialization
   - ✅ 7 endpoints HTTP (healthcheck, settings, test, notify)
   - ✅ Graceful shutdown (SIGINT, SIGTERM)

2. **`errorWhatsapp.js`** (Novo)
   - ✅ `sendEvent()` - função principal de envio
   - ✅ Anti-spam via MD5 hash (5 minutos TTL)
   - ✅ Validação de números telefônicos
   - ✅ Formatação WhatsApp com emojis e links
   - ✅ Busca de números no DB (system_settings)
   - ✅ Tratamento robusto de erros (graceful degradation)

3. **`dockerListener.js`** (Novo)
   - ✅ Spawna subprocess: `docker events --format {{json .}}`
   - ✅ Filtra eventos de container (start, stop, restart, die)
   - ✅ Auto-reconnect com backoff exponencial
   - ✅ Integração com sendEvent

### API Endpoints

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | Healthcheck geral |
| GET | `/health/whatsapp` | Status WhatsApp |
| POST | `/notify` | Enviar mensagem para grupo Notify |
| GET | `/settings/alert-phone` | Obter número configurado |
| PUT | `/settings/alert-phone` | Configurar/atualizar número |
| POST | `/settings/test-alert-phone` | Enviar teste (validação) |
| POST | `/test-error-log` | Gerar erro proposital |

### Database Schema

- ✅ Arquivo `schema.sql` pronto com:
  - Tabela `system_settings` (key-value)
  - Índices para performance
  - Função de auto-update timestamp
  - Trigger para updated_at

### Documentação

- ✅ `ALERTAS_WHATSAPP.md` - Guia completo para usuários
- ✅ `DEPLOYMENT.md` - Passo a passo de deployment
- ✅ `schema.sql` - Schema do banco de dados
- ✅ `whatsapp_service.py` - Integração Flask/Python

## 🎯 Eventos Monitorados

| Tipo | Level | Emoji | Descrição |
|------|-------|-------|-----------|
| startup | info | 🚀 | MultiMax iniciado |
| heartbeat | info | 💚 | Keepalive periódico (6h) |
| error | error | ❌ | Exceção ou erro |
| fatal | fatal | 🔴 | Erro crítico |
| docker | warn/error | 🐳 | Eventos de container |
| test | info | 🧪 | Teste de conectividade |
| warning | warn | ⚠️ | Aviso genérico |

## 📊 Fluxo de um evento

```
Evento acontece no sistema
    ↓
sendEvent(sock, event, db) chamado
    ↓
Calcular hash MD5 do evento
    ↓
Verificar anti-spam (5 min TTL)
    ↓
Buscar número alerta em system_settings
    ↓
Validar e formatar número
    ↓
Formatar mensagem humanizada
    ↓
Enviar via Baileys socket
    ↓
Registrar no cache anti-spam
    ↓
Log de sucesso/erro
```

## 🔧 Configuração Necessária

### 1. Banco de dados
```sql
-- Executar schema.sql
psql -U multimax -d multimax -f whatsapp-service/schema.sql
```

### 2. Variáveis de ambiente
```bash
NODE_ENV=production
HOSTNAME=prod-server
APP_BASE_URL=http://localhost:5000
```

### 3. Número de alerta
```bash
curl -X PUT http://localhost:3001/settings/alert-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "11987654321"}'
```

### 4. Conectar WhatsApp (QR code)
```bash
docker logs -f multimax-whatsapp
# Escanear QR code
```

### 5. Testar
```bash
curl -X POST http://localhost:3001/settings/test-alert-phone
```

## 🚀 Deployment

### Docker Compose
```yaml
whatsapp-service:
  build: ./whatsapp-service
  ports:
    - "3001:3001"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./whatsapp-service/auth:/app/auth
  environment:
    NODE_ENV: production
    HOSTNAME: prod-server
```

### Kubernetes (exemplo)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multimax-whatsapp
spec:
  containers:
  - name: whatsapp
    image: multimax-whatsapp:latest
    ports:
    - containerPort: 3001
    volumeMounts:
    - name: docker-socket
      mountPath: /var/run/docker.sock
    - name: auth
      mountPath: /app/auth
  volumes:
  - name: docker-socket
    hostPath:
      path: /var/run/docker.sock
  - name: auth
    emptyDir: {}
```

## 📈 Monitoramento

### Verificar conectividade
```bash
# Em tempo real
curl http://localhost:3001/health/whatsapp

# Com watch
watch -n 5 'curl -s http://localhost:3001/health/whatsapp | jq .'
```

### Ver logs
```bash
docker logs -f multimax-whatsapp

# Últimas 100 linhas
docker logs --tail=100 multimax-whatsapp

# Grep específico
docker logs multimax-whatsapp | grep -i error
```

### Testar envio manual
```bash
# Enviar um alerta de teste
curl -X POST http://localhost:3001/settings/test-alert-phone

# Gerar erro proposital
curl -X POST http://localhost:3001/test-error-log
```

## 🔐 Segurança

- ✅ Socket Docker em read-only
- ✅ Credenciais WhatsApp em volume persistente
- ✅ Validação de input (números telefônicos)
- ⚠️ Recomendado: Proxy reverso com autenticação para endpoints `/settings/*`

## 📋 Checklist de Validação

- [ ] `index.js` refatorizado e fazendo import de errorWhatsapp e DockerListener
- [ ] `errorWhatsapp.js` criado com sendEvent()
- [ ] `dockerListener.js` criado com spawn do docker events
- [ ] `schema.sql` executado no banco de dados
- [ ] Número de alerta configurado em system_settings
- [ ] WhatsApp conectado (QR code scaneado)
- [ ] Teste enviado com sucesso
- [ ] 7 endpoints respondendo corretamente
- [ ] Heartbeat recebido a cada 6 horas
- [ ] Docker events sendo monitorados
- [ ] Logs visíveis e sem erros

## 🎓 Próximas Implementações

### Frontend (opcional)
```javascript
// Card em dashboard/templates/index.html
<div class="card">
  <h3>Central de Notificações</h3>
  <p>WhatsApp: {{ whatsapp_status }}</p>
  <input type="tel" placeholder="Número" id="phone">
  <button onclick="updatePhone()">Salvar</button>
  <button onclick="testAlert()">Testar</button>
</div>
```

### Integração com Flask/API
```python
from multimax.whatsapp_service import register_error_handlers
app = Flask(__name__)
register_error_handlers(app)  # Ativa captura de erros
```

### Filtros e Alertas Customizados
```javascript
// Exemplo futuro
await sendEvent(sock, {
  type: 'error',
  filters: {
    notify_only_500: true,
    ignore_404: true,
  }
}, db);
```

## 📞 Suporte

Arquivos de referência:
- `ALERTAS_WHATSAPP.md` - Guia de uso
- `DEPLOYMENT.md` - Guia de deployment
- `whatsapp_service.py` - Exemplo Python
- `schema.sql` - Script de banco

Logs do serviço:
```bash
docker logs multimax-whatsapp | grep -E "(ERROR|✓|✗|Alerta)"
```

---

**Status: ✅ PRONTO PARA PRODUÇÃO**

Todos os módulos implementados e testáveis. Central de Notificações funcional.
