# MultiMax - Configuração Nginx

## Visão Geral

Nginx é recomendado como reverse proxy em produção para:
- ✅ Servir arquivos estáticos eficientemente
- ✅ Fazer load balancing
- ✅ Gerenciar SSL/TLS
- ✅ Caching de respostas
- ✅ Compressão (gzip)

---

## Configuração Básica

### 1. Habilitar Site

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/

# Desabilitar site padrão (opcional)
sudo rm /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Recarregar
sudo systemctl reload nginx
```

### 2. Configuração Padrão

O arquivo `/etc/nginx/sites-available/multimax` foi criado automaticamente pelo setup.

**Localização:** `/etc/nginx/sites-available/multimax`

**Conteúdo básico:**
```nginx
upstream multimax_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name seu-dominio.com;
    
    client_max_body_size 100M;

    location / {
        proxy_pass http://multimax_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/multimax/static/;
        expires 30d;
    }
}
```

---

## Configuração Avançada

### Com SSL/TLS (Let's Encrypt)

```bash
# 1. Instalar Certbot
sudo apt-get install certbot python3-certbot-nginx

# 2. Gerar certificado
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com

# 3. Renovação automática (já habilitada por padrão)
sudo systemctl enable certbot.timer
```

**Arquivo gerado:** `/etc/nginx/sites-available/multimax` (Certbot atualiza)

### Com Gzip (compressão)

```nginx
# Adicionar em /etc/nginx/sites-available/multimax

server {
    # ... configuração anterior ...

    # Compressão
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss;
    gzip_min_length 1000;
    gzip_vary on;
}
```

### Com Caching

```nginx
# Adicionar em /etc/nginx/sites-available/multimax

# Cache para arquivos estáticos
location /static/ {
    alias /opt/multimax/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Cache parcial para outros recursos
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Com Rate Limiting

```nginx
# Definir zona de rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    # ... configuração anterior ...

    # Limitar API a 10 req/s por IP
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://multimax_backend;
    }
}
```

### Com Log Customizado

```nginx
server {
    # ... configuração anterior ...

    # Logs detalhados
    access_log /var/log/nginx/multimax_access.log combined;
    error_log /var/log/nginx/multimax_error.log warn;

    # Log apenas erros 4xx e 5xx
    map $status $loggable {
        ~^[23] 0;
        default 1;
    }
    access_log /var/log/nginx/multimax_errors.log combined if=$loggable;
}
```

### Com múltiplos servidores (Load Balancing)

```nginx
upstream multimax_backend {
    # Distribuir entre múltiplos workers
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    
    # Ou usar IP/porta diferentes
    # server 192.168.1.10:5000;
    # server 192.168.1.11:5000;
}

server {
    # ... resto da configuração ...
}
```

---

## Exemplo Completo (Produção)

```nginx
# /etc/nginx/sites-available/multimax

# Upstream (backend Flask)
upstream multimax_backend {
    server 127.0.0.1:5000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Redirect HTTP para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name seu-dominio.com www.seu-dominio.com;
    
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name seu-dominio.com www.seu-dominio.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    # SSL Configuration (A+ rating)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Client limits
    client_max_body_size 100M;
    client_body_timeout 30s;
    client_header_timeout 30s;

    # Logs
    access_log /var/log/nginx/multimax_access.log combined;
    error_log /var/log/nginx/multimax_error.log warn;

    # Gzip
    gzip on;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss application/json;
    gzip_min_length 1000;
    gzip_vary on;

    # Static Files
    location /static/ {
        alias /opt/multimax/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # API Endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://multimax_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 60s;
    }

    # Aplicação principal
    location / {
        proxy_pass http://multimax_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # Health check
    location /health {
        proxy_pass http://multimax_backend/health;
        access_log off;
    }
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

---

## Verificar Configuração

```bash
# Sintaxe
sudo nginx -t

# Ver processos Nginx
ps aux | grep nginx

# Recarregar sem downtime
sudo systemctl reload nginx

# Restart (com downtime mínimo)
sudo systemctl restart nginx

# Ver status
sudo systemctl status nginx
```

---

## Troubleshooting

### Nginx retorna 502 Bad Gateway

```bash
# 1. Verificar se app está rodando
sudo systemctl status multimax

# 2. Testar conexão local
curl -I http://127.0.0.1:5000/

# 3. Ver erro do Nginx
sudo tail -20 /var/log/nginx/error.log

# 4. Checar permissões
sudo ls -la /var/log/nginx/
```

### HTTPS não funciona

```bash
# 1. Verificar certificado
sudo certbot certificates

# 2. Renovar certificado
sudo certbot renew --dry-run

# 3. Ver logs
sudo systemctl status certbot
```

### Muita latência

```bash
# 1. Habilitar keepalive
# (Já na config upstream acima)

# 2. Aumentar buffer
proxy_buffer_size 128k;
proxy_buffers 4 256k;

# 3. Ver upstream
upstream_connect_time $upstream_connect_time
upstream_header_time $upstream_header_time
upstream_response_time $upstream_response_time
```

---

## Monitoramento

### Ver requisições em tempo real

```bash
sudo tail -f /var/log/nginx/multimax_access.log
```

### Análise de tráfego

```bash
# Top 10 IPs
sudo awk '{print $1}' /var/log/nginx/multimax_access.log | sort | uniq -c | sort -rn | head -10

# Top 10 paths
sudo awk '{print $7}' /var/log/nginx/multimax_access.log | sort | uniq -c | sort -rn | head -10

# Status codes
sudo awk '{print $9}' /var/log/nginx/multimax_access.log | sort | uniq -c | sort -rn
```

---

**Última atualização:** 23 de janeiro de 2026  
**Nginx v1.24+** | **Ubuntu 24.04 LTS**
