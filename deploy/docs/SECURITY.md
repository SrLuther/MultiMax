# 🔐 Guia de Segurança MultiMax

> Implementação de segurança em camadas para produção

## 📋 Índice

1. [Pré-Deploy](#pré-deploy)
2. [Segurança do Sistema](#segurança-do-sistema)
3. [Segurança da Aplicação](#segurança-da-aplicação)
4. [Segurança do Banco de Dados](#segurança-do-banco-de-dados)
5. [Segurança de Rede](#segurança-de-rede)
6. [Monitoramento de Segurança](#monitoramento-de-segurança)
7. [Incident Response](#incident-response)

---

## ✅ Pré-Deploy

### Auditoria de Código

```bash
# Executar ferramentas de segurança
bandit -r /opt/multimax/app/multimax/
safety check --file /opt/multimax/app/requirements.txt
```

### Análise de Dependências

```bash
# Verificar vulnerabilidades
pip install pip-audit
pip-audit --desc
```

### Teste de Penetração Básico

```bash
# OWASP ZAP scan
zaproxy -cmd -quickurl https://seu-dominio.com -quickout /tmp/owasp-report.html
```

---

## 🛡️ Segurança do Sistema

### 1. Atualizações Automáticas

```bash
# Instalar unattended-upgrades
sudo apt-get install -y unattended-upgrades

# Configurar
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades

# Ativar
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 2. Auditoria de Sistema

```bash
# Instalar auditd
sudo apt-get install -y auditd

# Adicionar regras
sudo auditctl -w /opt/multimax/ -p wa -k multimax_changes
sudo auditctl -w /etc/nginx/ -p wa -k nginx_changes

# Ver eventos
sudo ausearch -k multimax_changes
```

### 3. Restrição de Privilégios

```bash
# Verificar sudoers
sudo visudo -c

# Limitar sudo
sudo visudo
# Adicionar:
multimax ALL=(ALL) NOPASSWD: /usr/bin/systemctl start multimax
multimax ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop multimax
```

### 4. SELinux/AppArmor

```bash
# Verificar status
sudo aa-status

# Criar perfil AppArmor para MultiMax (avançado)
sudo aa-genprof /opt/multimax/venv/bin/python
```

---

## 🔐 Segurança da Aplicação

### 1. Variáveis de Ambiente Seguras

```bash
# Nunca commit .env
echo ".env" >> /opt/multimax/app/.gitignore

# Permissões estritas
sudo chmod 600 /opt/multimax/.env
sudo chown multimax:multimax /opt/multimax/.env

# Verificar
ls -la /opt/multimax/.env
```

### 2. Secrets Management (Avançado)

```bash
# Usar HashiCorp Vault
curl https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip > vault.zip
unzip vault.zip && sudo mv vault /usr/local/bin/

# Inicializar Vault
vault server -dev

# Armazenar secrets
vault kv put secret/multimax SECRET_KEY=...
```

### 3. Rate Limiting

```python
# Em app.py (exemplo)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    pass
```

### 4. Proteção CSRF

```bash
# Verificar se Flask-WTF está configurado
grep -r "CSRFProtect" /opt/multimax/app/
```

### 5. Validação de Input

```bash
# Verificar uso de SQLAlchemy ORM (não SQL direto)
grep -r "execute(" /opt/multimax/app/ | grep -v venv
```

---

## 🗄️ Segurança do Banco de Dados

### 1. Restrição de Acesso

```bash
# Editar postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Configurações:
listen_addresses = '127.0.0.1'  # Apenas localhost
max_connections = 100
```

### 2. Backup Criptografado

```bash
# Backup com criptografia
sudo pg_dump multimax | gpg --symmetric --output backup.sql.gpg

# Restaurar
gpg --decrypt backup.sql.gpg | psql multimax
```

### 3. Logs do Banco

```bash
# Ativar logging
sudo nano /etc/postgresql/15/main/postgresql.conf

# Adicionar:
log_statement = 'all'
log_min_duration_statement = 1000  # Log queries > 1s
```

### 4. Teste de Integridade

```bash
# Verificar integridade
sudo -u postgres reindexdb multimax

# Vacuuming
sudo -u postgres vacuumdb --analyze multimax
```

---

## 🌐 Segurança de Rede

### 1. Firewall (UFW)

```bash
# Status
sudo ufw status

# Denegar por padrão
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (acesso remoto)
sudo ufw allow 22/tcp

# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# BLOQUEAR acesso direto à app
sudo ufw deny 5000/tcp

# Ativar
sudo ufw enable
```

### 2. IP Whitelisting (Produção)

```bash
# Se em VPC/intranet, restringir IPs
sudo nano /etc/nginx/sites-available/multimax

# Adicionar em server block:
allow 10.0.0.0/8;      # Sua rede privada
deny all;
```

### 3. DDoS Protection

```bash
# Instalar ModSecurity
sudo apt-get install -y libmodsecurity3 libmodsecurity-dev

# Configurar rate limiting
sudo nano /etc/nginx/sites-available/multimax

# Adicionar:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;
```

### 4. Certificado SSL Pinning (Avançado)

```bash
# Gerar HPKP header
openssl req -in /etc/letsencrypt/live/seu-dominio/cert.pem -pubkey -noout | \
openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | base64

# Adicionar ao Nginx
add_header Public-Key-Pins 'pin-sha256="..."; max-age=3600; includeSubDomains' always;
```

---

## 📊 Monitoramento de Segurança

### 1. Logs Centralizados

```bash
# Instalar Syslog-ng
sudo apt-get install -y syslog-ng

# Centralizar logs multimax
echo 'source multimax { file("/var/log/multimax/*"); };
destination syslog_server { tcp("log-server.example.com" port(514)); };
log { source(multimax); destination(syslog_server); };' | \
sudo tee /etc/syslog-ng/conf.d/multimax.conf

sudo systemctl restart syslog-ng
```

### 2. SIEM Integration (Produção)

```bash
# Splunk forwarder
wget -O splunkforwarder.deb 'https://...'
sudo dpkg -i splunkforwarder.deb

# Configurar inputs
sudo nano /opt/splunkforwarder/etc/system/local/inputs.conf
```

### 3. Alertas de Segurança

```bash
# Instalar AIDE (host-based intrusion detection)
sudo apt-get install -y aide aide-common

# Inicializar BD
sudo aideinit

# Agendar verificações
echo '0 2 * * * /usr/bin/aide --check' | sudo crontab -
```

### 4. File Integrity Monitoring

```bash
# Monitorar mudanças em arquivos críticos
sudo auditctl -w /opt/multimax/app -p wa -k app_changes
sudo auditctl -w /etc/nginx -p wa -k nginx_changes

# Usar Tripwire (alternativa)
sudo apt-get install -y tripwire
```

---

## 🚨 Incident Response

### 1. Detectar Comprometimento

```bash
# Processos suspeitos
ps aux | grep -E "python|nginx|postgres" | grep -v grep

# Conexões abertas
sudo netstat -tulnp | grep LISTEN

# Usuários logados
w
who

# Últimas modificações
find /opt/multimax -type f -mtime -1
```

### 2. Isolamento de Emergência

```bash
# Parar aplicação
sudo systemctl stop multimax

# Desconectar nginx
sudo systemctl stop nginx

# Desabilitar acesso
sudo ufw deny from any
```

### 3. Coletar Evidence

```bash
# Backup de logs
sudo tar -czf /tmp/multimax-incident.tar.gz \
  /var/log/multimax/ \
  /var/log/nginx/ \
  /var/log/postgresql/

# Cópia de processos
ps aux > /tmp/processes.txt
netstat -tulnp > /tmp/connections.txt

# Timeline de eventos
sudo ausearch -ts recent > /tmp/audit.log
```

### 4. Restore de Backup

```bash
# Verificar integridade de backup
sha256sum /opt/multimax/backups/multimax_db_*.sql.gz

# Restaurar
sudo multimax-db-restore.sh /opt/multimax/backups/backup-limpo.sql.gz

# Verificar código-fonte
cd /opt/multimax/app
git log --oneline -10
```

---

## 📋 Security Checklist

```
[ ] SECRET_KEY alterada e aleatória (32+ caracteres)
[ ] DEBUG=false em produção
[ ] HTTPS obrigatório com certificado válido
[ ] HSTS habilitado (min 31536000 segundos)
[ ] CSP headers configurados
[ ] CORS restrito a domínios específicos
[ ] Session cookies com flags Secure/HttpOnly/SameSite
[ ] Rate limiting ativado
[ ] Firewall (UFW) ativado com regras apropriadas
[ ] Fail2ban instalado para brute-force protection
[ ] PostgreSQL escutando apenas localhost
[ ] Backups criptografados e testados
[ ] Auditoria de sistema ativada (auditd)
[ ] Logs centralizados configurados
[ ] Alertas de segurança em place
[ ] Atualizações automáticas do SO ativadas
[ ] Penetration test realizado
[ ] Incident response plan documentado
[ ] Credenciais gerenciadas em secrets vault
[ ] API autenticação (JWT/OAuth2) implementada
```

---

**Última revisão:** Janeiro 2025  
**Responsável:** [Seu Nome]
