/**
 * whatsapp-service/DEPLOYMENT.md
 * 
 * Guia de deployment da Central de Notificações MultiMax
 */

# 🚀 Deployment da Central de Notificações

## Pré-requisitos

- Node.js 18+ (Para Baileys)
- Docker daemon rodando (para docker events)
- PostgreSQL com tabela `system_settings`
- Número de WhatsApp configurado e preparado

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  whatsapp-service:
    build:
      context: ./whatsapp-service
      dockerfile: Dockerfile
    container_name: multimax-whatsapp
    restart: unless-stopped
    
    environment:
      NODE_ENV: production
      HOSTNAME: ${HOSTNAME:-prod-server}
      APP_BASE_URL: ${APP_BASE_URL:-http://localhost:5000}
    
    # Expor porta HTTP
    ports:
      - "3001:3001"
    
    # Montar socket do Docker para eventos
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./whatsapp-service/auth:/app/auth  # Persistir sesão Baileys
    
    # Logs e reincio
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Network (conectar com API)
    networks:
      - multimax-network
```

## 1️⃣ Build da imagem

```bash
cd whatsapp-service

# Build local
docker build -t multimax-whatsapp:latest .

# Push para registry (opcional)
docker tag multimax-whatsapp:latest seu-registry.com/multimax-whatsapp:latest
docker push seu-registry.com/multimax-whatsapp:latest
```

## 2️⃣ Preparar banco de dados

```bash
# Conectar ao PostgreSQL
psql -U multimax -d multimax

# Executar schema SQL
\i whatsapp-service/schema.sql

# Verificar criação
SELECT * FROM system_settings;
```

## 3️⃣ Iniciar container

```bash
# Usando docker-compose
docker-compose up -d whatsapp-service

# Ou manualmente
docker run -d \
  --name multimax-whatsapp \
  -p 3001:3001 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./whatsapp-service/auth:/app/auth \
  -e HOSTNAME=prod-server \
  multimax-whatsapp:latest
```

## 4️⃣ Conectar WhatsApp

Após iniciar, você verá um QR code nos logs:

```bash
docker logs -f multimax-whatsapp
```

Escanear o QR code com seu WhatsApp.

## 5️⃣ Configurar número de alerta

```bash
# 1. Configurar número
curl -X PUT http://localhost:3001/settings/alert-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "11987654321"}'

# 2. Testar
curl -X POST http://localhost:3001/settings/test-alert-phone

# 3. Verificar saúde
curl http://localhost:3001/health/whatsapp
```

## 6️⃣ Integrar com API

Em seu `app.py` (ou outro entry point):

```python
from multimax.whatsapp_service import register_error_handlers

app = Flask(__name__)
register_error_handlers(app)  # Ativa captura de erros
```

## Monitoramento

### Logs
```bash
# Ver logs em tempo real
docker logs -f multimax-whatsapp

# Ver últimas 100 linhas
docker logs --tail=100 multimax-whatsapp

# Salvar logs em arquivo
docker logs multimax-whatsapp > whatsapp-service.log 2>&1
```

### Health Check
```bash
# Verificar serviço
curl http://localhost:3001/health
curl http://localhost:3001/health/whatsapp

# Monitorar com healthcheck automático
while true; do
  curl -s http://localhost:3001/health | jq .
  sleep 30
done
```

### Alertas WhatsApp
- Heartbeat: a cada 6 horas
- Erros: em tempo real
- Docker events: em tempo real
- Teste: sob demanda

## Troubleshooting

### ❌ QR Code não aparece
```bash
docker logs multimax-whatsapp | grep -i qr
```

Se não aparecer:
1. Remover pasta `auth/`: `rm -rf whatsapp-service/auth/*`
2. Reiniciar container: `docker restart multimax-whatsapp`
3. Ver logs novamente

### ❌ "Connection closed" repetido
- Número pode estar em outro dispositivo
- Ou sessão expirou
- Solução: repetir processo de QR code

### ❌ Não recebe alertas
1. Verificar número configurado: `curl http://localhost:3001/settings/alert-phone`
2. Testar envio: `curl -X POST http://localhost:3001/settings/test-alert-phone`
3. Ver logs: `docker logs multimax-whatsapp | tail -50`

### ❌ Docker events não funciona
```bash
# Verificar se docker socket está acessível
ls -la /var/run/docker.sock

# Testar docker eventos manualmente
docker events --format "{{json .}}" | head -5

# Dar permissão se necessário
sudo usermod -aG docker $USER
```

## Atualizar código

```bash
# 1. Build nova versão
docker build -t multimax-whatsapp:v2.0 .

# 2. Parar container atual
docker stop multimax-whatsapp

# 3. Remover container antigo
docker rm multimax-whatsapp

# 4. Iniciar novo
docker run -d --name multimax-whatsapp ... (mesmo comando acima)

# 5. Verificar
docker logs multimax-whatsapp
```

## Backup e Restore

### Backup de credenciais WhatsApp
```bash
# Copiar pasta auth
cp -r whatsapp-service/auth ./backups/auth-$(date +%Y%m%d).tar.gz

# Compactar
tar -czf auth-backup.tar.gz whatsapp-service/auth/
```

### Restore de credenciais
```bash
# Extrair
tar -xzf auth-backup.tar.gz

# Reiniciar
docker restart multimax-whatsapp
```

## Performance

- Uso de RAM: ~150-200MB
- CPU: < 1% idle (picos durante erros)
- Conexão: sempre ativa (1 conexão WebSocket)
- Taxa de eventos: ~10-100/hora típico

## Segurança

- ✅ Socket Docker em modo read-only
- ✅ Credenciais WhatsApp em volume persistente
- ✅ HTTP localmente (usar proxy reverso em produção)
- ⚠️ Número de alerta em banco de dados (considerar criptografia)

## Próximas etapas

1. [ ] Implementar autenticação nos endpoints
2. [ ] Adicionar múltiplos números de alerta
3. [ ] Dashboard de histórico
4. [ ] Integração com Prometheus/Grafana
5. [ ] CI/CD automatizado
