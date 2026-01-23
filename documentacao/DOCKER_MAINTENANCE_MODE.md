# Exemplo de docker-compose.yml com Modo de Manutenção

## Para ativar o modo de manutenção no Docker Compose:

### Opção 1: Adicionar variável diretamente no docker-compose.yml

```yaml
version: '3.9'

services:
  multimax:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: multimax
    ports:
      - "5000:5000"
    volumes:
      - /opt/multimax-data:/multimax-data
      - /opt/multimax:/opt/multimax:ro
    environment:
      - HOST=0.0.0.0
      - PORT=5000
      - DEBUG=false
      - GIT_REPO_DIR=/opt/multimax
      - MAINTENANCE_MODE=false  # ← Adicione esta linha
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Opção 2: Usar arquivo .env

Criar arquivo `.env` no mesmo diretório do `docker-compose.yml`:

```env
MAINTENANCE_MODE=false
```

E referenciar no docker-compose.yml:

```yaml
services:
  multimax:
    # ... outras configurações
    env_file:
      - .env
```

## Como ativar/desativar

### Método 1: Editar docker-compose.yml

1. Altere `MAINTENANCE_MODE=true` no arquivo
2. Execute: `docker-compose up -d` ou `docker-compose restart`

### Método 2: Sobrescrever via comando

```bash
# Ativar modo de manutenção
docker-compose run -e MAINTENANCE_MODE=true multimax

# Ou reiniciar com variável
docker-compose down
MAINTENANCE_MODE=true docker-compose up -d
```

### Método 3: Alterar variável de ambiente do container em execução

```bash
# Parar container
docker-compose stop multimax

# Editar docker-compose.yml para MAINTENANCE_MODE=true

# Iniciar novamente
docker-compose up -d
```

## Verificar status

```bash
# Ver logs do container
docker-compose logs multimax | grep MANUTENÇÃO

# Se modo ativo, você verá:
# ⚠️  MODO DE MANUTENÇÃO ATIVO - Sistema bloqueado

# Testar endpoint
curl -I http://localhost:5000
# Deve retornar: HTTP/1.1 503 Service Unavailable (se modo ativo)
```

## Notas importantes

- Sempre use `docker-compose restart` ou `docker-compose up -d` após alterar variáveis
- O healthcheck pode falhar quando modo de manutenção está ativo (HTTP 503)
- Considere desabilitar o healthcheck ou ajustá-lo durante manutenção
