# Infraestrutura do WhatsApp Service - MultiMax

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS (443)
                            ▼
                    ┌───────────────┐
                    │  Nginx Proxy  │
                    │  (Port 443)   │
                    └───────┬───────┘
                            │
              ┌─────────────┴──────────────┐
              │                            │
              ▼                            ▼
    ┌──────────────────┐         ┌──────────────────┐
    │  MultiMax App    │         │ WhatsApp Service │
    │  (Docker:5000)   │         │  (Node:3001)     │
    │                  │         │  [systemd]       │
    └──────────────────┘         └──────────────────┘
           │                              │
           └──────────────┐  ┌────────────┘
                          ▼  ▼
                    ┌─────────────┐
                    │  WhatsApp   │
                    │   Groups    │
                    └─────────────┘
```

### Fluxo de Comunicação

1. **Usuário acessa:** `https://www.multimax.tec.br`
2. **Nginx recebe** e roteia:
   - `/` → Container Docker (porta 5000)
   - `/notify` → WhatsApp Service (porta 3001)
3. **MultiMax envia notificação:** POST `https://www.multimax.tec.br/notify`
4. **WhatsApp Service processa** e envia para grupos

---

## Por Que Nginx é Necessário?

### 🚫 Problema: Containers não acessam localhost do host

```bash
# DENTRO DO CONTAINER:
curl http://localhost:3001/notify  # ❌ FALHA
# localhost = rede interna do container, NÃO do host
```

### ✅ Solução: Usar domínio externo + proxy reverso

```bash
# DENTRO DO CONTAINER:
curl https://www.multimax.tec.br/notify  # ✅ FUNCIONA
# Nginx roteia para 127.0.0.1:3001 no host
```

### Razões Técnicas

1. **Isolamento de Rede Docker:**
   - Containers têm stack de rede própria
   - `localhost` aponta para dentro do container
   - `host.docker.internal` não é confiável em produção

2. **Simplicidade de Configuração:**
   - Uma única URL para todos os ambientes
   - Sem necessidade de mapeamento de portas complexo
   - Certificado SSL centralizado no Nginx

3. **Segurança:**
   - WhatsApp Service não exposto diretamente
   - Firewall pode bloquear porta 3001 externamente
   - SSL/TLS gerenciado pelo Nginx

4. **Escalabilidade:**
   - Fácil adicionar rate limiting
   - Fácil adicionar autenticação no proxy
   - Fácil migrar para load balancer

---

## Requisitos da VPS

### Software Necessário

| Componente | Versão Mínima | Instalação |
|------------|---------------|------------|
| **Node.js** | 18+ | `curl -fsSL https://deb.nodesource.com/setup_18.x \| sudo -E bash -` |
| **npm** | 8+ | Incluído com Node.js |
| **Nginx** | 1.18+ | `sudo apt install nginx` |
| **systemd** | 245+ | Incluído no Ubuntu 20.04+ |
| **Certbot** | 1.0+ | `sudo apt install certbot python3-certbot-nginx` |
| **Docker** | 20.10+ | Requerido para MultiMax |

### Portas Utilizadas

| Porta | Serviço | Exposição | Firewall |
|-------|---------|-----------|----------|
| **443** | Nginx (HTTPS) | Externa | ✅ Aberta |
| **80** | Nginx (HTTP→HTTPS redirect) | Externa | ✅ Aberta |
| **5000** | MultiMax (Docker) | Interna | ❌ Fechada |
| **3001** | WhatsApp Service | Interna | ❌ Fechada |

**⚠️ IMPORTANTE:** Portas 5000 e 3001 NUNCA devem ser expostas publicamente.

---

## Configuração do Nginx

### Arquivo: `/etc/nginx/sites-available/multimax`

```nginx
# Redirecionar HTTP para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name www.multimax.tec.br multimax.tec.br;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirecionar tudo para HTTPS
    location / {
        return 301 https://www.multimax.tec.br$request_uri;
    }
}

# Configuração HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.multimax.tec.br multimax.tec.br;

    # Certificados SSL (gerenciados pelo Certbot)
    ssl_certificate /etc/letsencrypt/live/www.multimax.tec.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.multimax.tec.br/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/multimax_access.log;
    error_log /var/log/nginx/multimax_error.log;

    # WhatsApp Service endpoint
    location /notify {
        proxy_pass http://127.0.0.1:3001/notify;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts para requisições WhatsApp
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;

        # Tamanho máximo do corpo da requisição
        client_max_body_size 10M;
    }

    # MultiMax Application (todas as outras rotas)
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts para aplicação Flask
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Tamanho máximo do upload
        client_max_body_size 50M;
    }
}
```

### Ativação

```bash
# Criar symlink para sites-enabled
sudo ln -sf /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/

# Remover default se existir
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

---

## Serviço systemd do WhatsApp

### Arquivo: `/etc/systemd/system/whatsapp-service.service`

```ini
[Unit]
Description=WhatsApp Service for MultiMax (Baileys)
Documentation=https://github.com/SrLuther/MultiMax
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=multimax
Group=multimax
WorkingDirectory=/opt/multimax/whatsapp-service
ExecStart=/usr/bin/node index.js
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=whatsapp-service

# Variáveis de ambiente (opcional)
# Environment="NODE_ENV=production"

# Limites de recursos
LimitNOFILE=65536
MemoryLimit=512M

# Segurança
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/multimax/whatsapp-service/auth

[Install]
WantedBy=multi-user.target
```

### Gerenciamento do Serviço

```bash
# Recarregar configurações do systemd
sudo systemctl daemon-reload

# Habilitar para iniciar no boot
sudo systemctl enable whatsapp-service

# Iniciar serviço
sudo systemctl start whatsapp-service

# Verificar status
sudo systemctl status whatsapp-service

# Ver logs em tempo real
sudo journalctl -u whatsapp-service -f

# Reiniciar serviço
sudo systemctl restart whatsapp-service

# Parar serviço
sudo systemctl stop whatsapp-service
```

---

## Variáveis de Ambiente

### MultiMax (Container Docker)

**Arquivo:** `.env` ou variáveis do Docker Compose

```bash
# URL do endpoint WhatsApp (OBRIGATÓRIO em produção)
WHATSAPP_NOTIFY_URL=https://www.multimax.tec.br/notify

# Timeout para requisições WhatsApp (opcional, padrão: 8 segundos)
WHATSAPP_NOTIFY_TIMEOUT=8

# Habilitar notificações automáticas (opcional, padrão: false)
NOTIFICACOES_ENABLED=false
```

### WhatsApp Service (systemd)

**Arquivo:** `/etc/systemd/system/whatsapp-service.service` ou `/opt/multimax/whatsapp-service/.env`

```bash
# Ambiente Node.js (opcional)
NODE_ENV=production

# Log level do Pino (opcional)
LOG_LEVEL=info
```

---

## Instalação Completa (Manual)

### 1. Preparar Diretório

```bash
# Criar usuário dedicado
sudo useradd -r -m -s /bin/bash multimax

# Criar diretório do serviço
sudo mkdir -p /opt/multimax/whatsapp-service
sudo chown multimax:multimax /opt/multimax/whatsapp-service
```

### 2. Instalar Node.js 18+

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node --version  # Verificar: v18.x ou superior
```

### 3. Deploy do WhatsApp Service

```bash
# Copiar arquivos do projeto
sudo -u multimax cp -r whatsapp-service/* /opt/multimax/whatsapp-service/

# Instalar dependências
cd /opt/multimax/whatsapp-service
sudo -u multimax npm install

# Criar pasta de autenticação
sudo -u multimax mkdir -p /opt/multimax/whatsapp-service/auth
```

### 4. Configurar systemd

```bash
# Criar arquivo de serviço
sudo nano /etc/systemd/system/whatsapp-service.service
# (colar configuração acima)

# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar e iniciar
sudo systemctl enable whatsapp-service
sudo systemctl start whatsapp-service
```

### 5. Instalar e Configurar Nginx

```bash
# Instalar Nginx
sudo apt install -y nginx

# Criar configuração
sudo nano /etc/nginx/sites-available/multimax
# (colar configuração acima)

# Ativar site
sudo ln -sf /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar e recarregar
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Configurar SSL com Certbot

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obter certificado (interativo)
sudo certbot --nginx -d www.multimax.tec.br -d multimax.tec.br

# Renovação automática já está configurada via cron
```

### 7. Autenticar WhatsApp

```bash
# Ver logs em tempo real
sudo journalctl -u whatsapp-service -f

# O QR Code aparecerá nos logs
# Escanear com WhatsApp no celular:
# Configurações > Aparelhos conectados > Conectar dispositivo
```

---

## Checklist de Validação Pós-Instalação

### ✅ Serviço WhatsApp

```bash
# Status do serviço
sudo systemctl status whatsapp-service
# Esperado: active (running)

# Verificar logs
sudo journalctl -u whatsapp-service -n 50
# Esperado: "Servidor HTTP rodando na porta 3001 e acessível externamente"

# Teste local
curl -X POST http://localhost:3001/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Teste local"}'
# Esperado: {"sucesso":true,"mensagem":"Enviado para grupo Notify"}
```

### ✅ Nginx

```bash
# Status do Nginx
sudo systemctl status nginx
# Esperado: active (running)

# Testar configuração
sudo nginx -t
# Esperado: syntax is ok, test is successful

# Verificar portas
sudo netstat -tulpn | grep nginx
# Esperado: 0.0.0.0:80 e 0.0.0.0:443
```

### ✅ SSL/HTTPS

```bash
# Verificar certificado
sudo certbot certificates
# Esperado: Certificate Name: www.multimax.tec.br, Valid, Not due for renewal

# Teste HTTPS
curl -I https://www.multimax.tec.br
# Esperado: HTTP/2 200
```

### ✅ Endpoint Público

```bash
# Teste via domínio (de qualquer máquina)
curl -X POST https://www.multimax.tec.br/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Teste público"}'
# Esperado: {"sucesso":true,"mensagem":"Enviado para grupo Notify"}
```

### ✅ Conectividade do Container

```bash
# DENTRO do container MultiMax
docker exec -it multimax_container bash
curl -X POST https://www.multimax.tec.br/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Teste do container"}'
# Esperado: {"sucesso":true,"mensagem":"Enviado para grupo Notify"}
```

### ✅ Firewall

```bash
# Verificar regras (se UFW estiver ativo)
sudo ufw status
# Esperado: 80/tcp ALLOW, 443/tcp ALLOW, 3001/tcp DENY
```

---

## Comandos de Diagnóstico

### Logs do WhatsApp Service

```bash
# Últimas 100 linhas
sudo journalctl -u whatsapp-service -n 100

# Seguir em tempo real
sudo journalctl -u whatsapp-service -f

# Filtrar por erros
sudo journalctl -u whatsapp-service -p err

# Logs de hoje
sudo journalctl -u whatsapp-service --since today
```

### Logs do Nginx

```bash
# Access log (últimas requisições)
sudo tail -f /var/log/nginx/multimax_access.log

# Error log
sudo tail -f /var/log/nginx/multimax_error.log

# Filtrar requisições para /notify
sudo grep "/notify" /var/log/nginx/multimax_access.log
```

### Teste de Conectividade

```bash
# Verificar se porta 3001 está escutando
sudo netstat -tulpn | grep 3001
# Esperado: 0.0.0.0:3001 ... node

# Verificar processo Node
ps aux | grep "node.*index.js"

# Teste de latência
time curl -X POST http://localhost:3001/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Latency test"}'
```

---

## Troubleshooting Comum

### Erro: "Grupo Notify não encontrado"

**Causa:** Grupo "Notify" não existe no WhatsApp conectado

**Solução:**
1. Criar grupo WhatsApp chamado "Notify" (case-insensitive)
2. Reiniciar serviço: `sudo systemctl restart whatsapp-service`
3. Verificar logs para confirmação

### Erro: "WhatsApp não está conectado"

**Causa:** Sessão do WhatsApp expirada ou não autenticada

**Solução:**
```bash
# Ver logs para QR Code
sudo journalctl -u whatsapp-service -f

# Se sessão expirou, limpar e reiniciar
sudo systemctl stop whatsapp-service
sudo rm -rf /opt/multimax/whatsapp-service/auth/*
sudo systemctl start whatsapp-service
# Escanear novo QR Code
```

### Erro: "502 Bad Gateway" no /notify

**Causa:** WhatsApp Service não está rodando

**Solução:**
```bash
# Verificar status
sudo systemctl status whatsapp-service

# Iniciar se parado
sudo systemctl start whatsapp-service

# Ver logs de erro
sudo journalctl -u whatsapp-service -n 50
```

### Erro: "Connection refused" do container

**Causa:** Nginx não está roteando corretamente

**Solução:**
```bash
# Testar Nginx localmente
curl -I http://localhost:3001/notify
# Se funciona localmente, problema é no Nginx

# Verificar configuração Nginx
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

---

## Manutenção

### Atualizar WhatsApp Service

```bash
# Parar serviço
sudo systemctl stop whatsapp-service

# Fazer backup da sessão
sudo cp -r /opt/multimax/whatsapp-service/auth /opt/multimax/auth_backup

# Atualizar código
cd /opt/multimax/whatsapp-service
sudo -u multimax git pull  # ou copiar novos arquivos

# Reinstalar dependências
sudo -u multimax npm install

# Restaurar sessão
sudo cp -r /opt/multimax/auth_backup/* /opt/multimax/whatsapp-service/auth/

# Reiniciar serviço
sudo systemctl start whatsapp-service
```

### Renovação SSL (automática)

```bash
# Certbot configura cron automaticamente
# Para forçar renovação:
sudo certbot renew --dry-run  # Teste
sudo certbot renew           # Renovar se necessário
```

### Backup da Sessão WhatsApp

```bash
# Criar backup
sudo tar -czf whatsapp-session-$(date +%Y%m%d).tar.gz \
  /opt/multimax/whatsapp-service/auth/

# Restaurar backup
sudo systemctl stop whatsapp-service
sudo tar -xzf whatsapp-session-20260122.tar.gz -C /
sudo chown -R multimax:multimax /opt/multimax/whatsapp-service/auth
sudo systemctl start whatsapp-service
```

---

## Migração para Nova VPS

### Checklist de Migração

1. **Exportar sessão WhatsApp:**
   ```bash
   # Na VPS antiga
   sudo tar -czf whatsapp-session.tar.gz /opt/multimax/whatsapp-service/auth/
   ```

2. **Configurar nova VPS:**
   - Executar script de automação ou instalação manual
   - Configurar DNS apontando para novo IP

3. **Importar sessão:**
   ```bash
   # Na VPS nova
   sudo tar -xzf whatsapp-session.tar.gz -C /
   sudo chown -R multimax:multimax /opt/multimax/whatsapp-service/auth
   ```

4. **Configurar SSL:**
   ```bash
   sudo certbot --nginx -d www.multimax.tec.br -d multimax.tec.br
   ```

5. **Validar tudo:**
   - Seguir checklist de validação acima

---

## Referências

- **Baileys WhatsApp:** https://github.com/WhiskeySockets/Baileys
- **Nginx Proxy:** https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **Systemd Services:** https://www.freedesktop.org/software/systemd/man/systemd.service.html
- **Certbot:** https://certbot.eff.org/

---

## Suporte e Issues

Para reportar problemas ou sugestões:
- **GitHub:** https://github.com/SrLuther/MultiMax/issues
- **Logs importantes:** Sempre anexar saída de:
  - `sudo journalctl -u whatsapp-service -n 100`
  - `sudo tail -n 50 /var/log/nginx/multimax_error.log`
