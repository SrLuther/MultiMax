# 📚 MultiMax Deployment Guide - Ubuntu 24.04 LTS

> Guia técnico completo para deploy, operação e manutenção do MultiMax em servidores Linux

**Versão:** 1.0.0  
**Última atualização:** Janeiro 2025  
**Status:** ✅ Pronto para Produção

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Instalação Rápida](#instalação-rápida)
4. [Instalação Manual](#instalação-manual-passo-a-passo)
5. [Configuração](#configuração)
6. [Operação](#operação)
7. [Monitoramento](#monitoramento)
8. [Troubleshooting](#troubleshooting)
9. [Segurança](#segurança)
10. [Backup e Restore](#backup-e-restore)
11. [Atualização](#atualização)

---

## 🎯 Visão Geral

### Arquitetura

```
┌─────────────┐
│   Cliente   │
│  (Browser)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────┐
│   Nginx Reverso     │  Port 80/443
│     Proxy Server    │
└──────┬──────────────┘
       │ HTTP Local
       ▼
┌─────────────────────┐
│  Flask Application  │  Port 5000
│   (Waitress WSGI)   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   PostgreSQL 15+    │  Port 5432
│   Database Server   │
└─────────────────────┘
```

### Componentes

| Componente | Versão | Porta | Propósito |
|-----------|--------|-------|----------|
| Ubuntu | 24.04 LTS | - | Sistema Operacional |
| Python | 3.11+ | - | Runtime |
| Flask | 2.3+ | - | Web Framework |
| PostgreSQL | 15+ | 5432 | Database |
| Nginx | 1.24+ | 80/443 | Proxy Reverso |
| Waitress | 2.1+ | 5000 | WSGI Server |

---

## 📦 Pré-requisitos

### Hardware Mínimo (Desenvolvimento)
- **CPU:** 1 core (2+ recomendado)
- **RAM:** 512MB (2GB recomendado)
- **Disco:** 10GB SSD (mínimo para app + dados)
- **Conexão:** Internet estável

### Hardware Recomendado (Produção)
- **CPU:** 4 cores (ARM64 suportado)
- **RAM:** 8GB+
- **Disco:** 100GB+ SSD com RAID
- **Conexão:** Banda larga dedicada

### Software Obrigatório
- ✅ Ubuntu 24.04 LTS (ou derivado)
- ✅ Acesso root ou sudo
- ✅ Conexão SSH (recomendado)
- ✅ Git (para clone do repositório)

### Domínio e SSL
- ✅ Domínio DNS configurado apontando para seu servidor
- ✅ Certificado SSL (Let's Encrypt grátis recomendado)

---

## ⚡ Instalação Rápida

Para instalação automatizada em 5 minutos:

```bash
# 1. Fazer login como root
sudo su -

# 2. Baixar script de setup
curl -O https://raw.githubusercontent.com/SrLuther/MultiMax/main/deploy/scripts/setup.sh
chmod +x setup.sh

# 3. Executar setup (prepara tudo automaticamente)
bash setup.sh

# 4. Configurar domínio e SSL
sudo nano /etc/nginx/sites-available/multimax
# Altere "YOUR_DOMAIN_HERE" para seu domínio real

# 5. Gerar certificado SSL (Let's Encrypt)
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d seu-dominio.com

# 6. Editar arquivo .env
sudo nano /opt/multimax/.env
# Configure SECRET_KEY, DATABASE_URL, etc

# 7. Iniciar aplicação
sudo systemctl start multimax
sudo systemctl status multimax
```

**Pronto!** 🎉 Acesse `https://seu-dominio.com`

---

## 🔧 Instalação Manual Passo-a-Passo

Para instalações mais controladas ou troubleshooting:

### 1️⃣ Atualizar Sistema Operacional

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential git curl wget
```

### 2️⃣ Instalar Python 3.11

```bash
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
python3.11 --version  # Verificar
```

### 3️⃣ Instalar PostgreSQL

```bash
sudo apt-get install -y postgresql postgresql-contrib postgresql-client
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verificar status
sudo systemctl status postgresql
```

### 4️⃣ Criar Usuário e Banco de Dados

```bash
# Acessar console PostgreSQL
sudo -u postgres psql

# Dentro do psql:
CREATE USER multimax WITH PASSWORD 'multimax123';
CREATE DATABASE multimax OWNER multimax ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE multimax TO multimax;
\q  # Sair
```

### 5️⃣ Criar Usuário da Aplicação

```bash
sudo useradd -r -s /bin/bash -d /opt/multimax -m multimax
sudo mkdir -p /opt/multimax/{app,logs,tmp,backups,.env}
sudo chown -R multimax:multimax /opt/multimax
sudo chmod 750 /opt/multimax
```

### 6️⃣ Clonar Repositório

```bash
cd /opt/multimax
sudo -u multimax git clone https://github.com/SrLuther/MultiMax.git app
cd app
sudo -u multimax git checkout main  # ou branch específico
```

### 7️⃣ Configurar Python Virtual Environment

```bash
sudo -u multimax python3.11 -m venv /opt/multimax/venv
source /opt/multimax/venv/bin/activate

# Instalar dependências
pip install --upgrade pip setuptools wheel
pip install -r /opt/multimax/app/requirements.txt

# Desativar venv
deactivate
```

### 8️⃣ Configurar Arquivo .env

```bash
sudo nano /opt/multimax/.env
```

**Copie e customize:**
```env
FLASK_ENV=production
DEBUG=false
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=postgresql://multimax:multimax123@localhost:5432/multimax
HOST=127.0.0.1
PORT=5000
LOG_LEVEL=INFO
LOG_FILE=/var/log/multimax/app.log
```

```bash
sudo chown multimax:multimax /opt/multimax/.env
sudo chmod 600 /opt/multimax/.env
```

### 9️⃣ Inicializar Banco de Dados

```bash
sudo -u multimax bash -c \
  "source /opt/multimax/venv/bin/activate && \
   cd /opt/multimax/app && \
   FLASK_APP=app.py flask db upgrade"
```

### 🔟 Configurar Systemd Service

```bash
sudo nano /etc/systemd/system/multimax.service
```

Copie o arquivo `deploy/systemd/multimax.service` e customize conforme necessário.

```bash
sudo systemctl daemon-reload
sudo systemctl enable multimax.service
sudo systemctl start multimax
```

### 1️⃣1️⃣ Instalar e Configurar Nginx

```bash
sudo apt-get install -y nginx
sudo nano /etc/nginx/sites-available/multimax
```

Copie a configuração de `deploy/config/nginx-multimax.conf` e **customize:**
- Troque `YOUR_DOMAIN_HERE` pelo seu domínio
- Configure caminhos de SSL

```bash
sudo ln -sf /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t  # Testar configuração
sudo systemctl restart nginx
```

### 1️⃣2️⃣ Gerar Certificado SSL (Let's Encrypt)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d seu-dominio.com -d www.seu-dominio.com
sudo certbot renew --dry-run  # Testar renovação automática
```

### 1️⃣3️⃣ Criar Diretório de Logs

```bash
sudo mkdir -p /var/log/multimax
sudo chown multimax:multimax /var/log/multimax
sudo chmod 755 /var/log/multimax
```

### 1️⃣4️⃣ Testes de Sanidade

```bash
# Verificar serviços
sudo systemctl status multimax postgresql nginx

# Testar conectividade
curl http://127.0.0.1:5000/
curl https://seu-dominio.com/

# Verificar logs
sudo journalctl -u multimax -f
```

---

## ⚙️ Configuração

### Arquivo `.env` - Variáveis Essenciais

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `FLASK_ENV` | `production` | Ambiente (production/development) |
| `DEBUG` | `false` | Modo debug (NUNCA true em produção) |
| `SECRET_KEY` | `abc123...` | Chave para sessões (gerar nova) |
| `DATABASE_URL` | `postgresql://user:pass@host/db` | String de conexão DB |
| `HOST` | `127.0.0.1` | IP bind da aplicação |
| `PORT` | `5000` | Porta da aplicação |
| `LOG_LEVEL` | `INFO` | Nível de log (DEBUG/INFO/WARNING/ERROR) |

### Geração de SECRET_KEY Segura

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
# Copie a saída para SECRET_KEY no .env
```

### Configurar Banco de Dados Remoto (Opcional)

Se usar PostgreSQL remoto:

```bash
# .env
DATABASE_URL=postgresql://user:password@remote-host.com:5432/multimax

# Testar conexão
psql postgresql://user:password@remote-host.com:5432/multimax
```

### Habilitar Logs Estruturados

```bash
# .env
LOG_LEVEL=INFO
LOG_FILE=/var/log/multimax/app.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=10     # Manter 10 backups
```

---

## 🚀 Operação

### Comandos Systemd

```bash
# Iniciar aplicação
sudo systemctl start multimax

# Parar aplicação
sudo systemctl stop multimax

# Reiniciar aplicação
sudo systemctl restart multimax

# Status completo
sudo systemctl status multimax

# Ver logs em tempo real
sudo journalctl -u multimax -f

# Ver últimas N linhas
sudo journalctl -u multimax -n 100
```

### Scripts de Operação

Scripts prontos em `/usr/local/bin/`:

```bash
# Iniciar
sudo multimax-start.sh

# Parar
sudo multimax-stop.sh

# Reiniciar
sudo multimax-restart.sh

# Ver status
sudo multimax-status.sh

# Ver logs
sudo multimax-logs.sh [linhas]

# Atualizar código
sudo multimax-update.sh

# Backup BD
sudo multimax-db-backup.sh
```

### Modo de Manutenção

Para manutenção sem interromper completamente:

```bash
# Ativar modo manutenção
sudo touch /opt/multimax/.maintenance

# Acessar:  Seu site mostrará página de manutenção

# Desativar
sudo rm /opt/multimax/.maintenance
```

### Redeploy de Código

Para atualizar código da aplicação:

```bash
# Opção 1: Usar script de atualização (recomendado)
sudo multimax-update.sh

# Opção 2: Manual
cd /opt/multimax/app
sudo -u multimax git pull origin main
source /opt/multimax/venv/bin/activate
pip install -r requirements.txt
FLASK_APP=app.py flask db upgrade
deactivate
sudo systemctl restart multimax
```

---

## 📊 Monitoramento

### Verificar Saúde da Aplicação

```bash
# Endpoint de health check (sem autenticação)
curl https://seu-dominio.com/health

# Resposta esperada: HTTP 200 OK
```

### Monitorar Recursos

```bash
# Ver uso de CPU e memória
top

# Processos Python específicos
ps aux | grep python

# Espaço em disco
df -h /opt/multimax
du -sh /opt/multimax/*
```

### Monitora Port/Sockets

```bash
# Verificar porta 5000
netstat -tlnp | grep 5000
# ou
ss -tlnp | grep 5000
```

### Logs Principais

| Arquivo | Propósito |
|---------|-----------|
| `/var/log/multimax/app.log` | Logs da aplicação |
| `/var/log/nginx/multimax_access.log` | Requisições HTTP |
| `/var/log/nginx/multimax_error.log` | Erros Nginx |
| `/var/log/postgresql/postgresql.log` | Logs BD |

### Verificação de Conexões BD

```bash
# Listar conexões ativas
psql -U multimax -d multimax -c "SELECT * FROM pg_stat_activity;"

# Contar conexões
psql -U multimax -d multimax -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 🔍 Troubleshooting

### Aplicação não inicia

```bash
# Ver erro específico
sudo journalctl -u multimax -n 50 -p err

# Tentar iniciar em primeiro plano (debug)
cd /opt/multimax/app
source /opt/multimax/venv/bin/activate
python app.py  # Ctrl+C para parar
```

### Erro: "Permission denied"

```bash
# Verificar permissões
ls -la /opt/multimax
sudo chown -R multimax:multimax /opt/multimax
sudo chmod 750 /opt/multimax
```

### Erro: "Connection refused" no banco

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# Testar conexão
psql -U multimax -d multimax -h localhost
```

### Nginx retorna 502 Bad Gateway

```bash
# Verificar se aplicação está rodando
sudo systemctl status multimax

# Verificar socket/porta
sudo netstat -tlnp | grep 5000

# Ver erro no Nginx
sudo tail -50 /var/log/nginx/multimax_error.log

# Reiniciar
sudo systemctl restart multimax nginx
```

### Memória/CPU elevada

```bash
# Identificar processo
top -b -n 1 | head -20

# Variáveis de limite (em .env)
# MemoryMax=512M  (arquivo systemd)
# TasksMax=256    (arquivo systemd)

# Reiniciar com limite
sudo systemctl restart multimax
```

### Disco cheio

```bash
# Encontrar arquivos grandes
du -sh /opt/multimax/* | sort -h | tail

# Limpar backups antigos
rm /opt/multimax/backups/multimax_db_*.sql.gz

# Limpar cache/temp
rm -rf /opt/multimax/tmp/*
```

### SSL/Certificate Issues

```bash
# Verificar validade
sudo certbot certificates

# Renovar manualmente
sudo certbot renew --force-renewal

# Verificar arquivo
openssl x509 -in /etc/letsencrypt/live/seu-dominio.com/cert.pem -text -noout
```

---

## 🔐 Segurança

### Checklist de Segurança

- [ ] `SECRET_KEY` alterado e aleatório
- [ ] `DEBUG=false` em produção
- [ ] Certificado SSL válido
- [ ] HSTS ativado (nginx)
- [ ] Firewall configurado
- [ ] SSH com chaves (não password)
- [ ] Sudo sem password desabilitado
- [ ] Backups automatizados
- [ ] Logs centralizados
- [ ] Atualizações do SO regulares

### Configurar Firewall

```bash
# UFW (Ubuntu Firewall)
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Bloquear acesso direto à porta 5000
sudo ufw deny 5000/tcp
```

### Proteger Arquivo .env

```bash
# Permissões corretas
sudo chmod 600 /opt/multimax/.env
sudo chown multimax:multimax /opt/multimax/.env

# Não commit no git
echo ".env" >> .gitignore
```

### Habilitar Fail2Ban

```bash
# Instalar
sudo apt-get install -y fail2ban

# Configurar para Nginx
sudo nano /etc/fail2ban/jail.d/nginx-http-auth.conf

# Ativar
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Backup de Dados Sensíveis

```bash
# Criptografar backup
gpg --symmetric /opt/multimax/backups/multimax_db_*.sql.gz

# Ou usar 7zip com senha
7z a -p /opt/multimax/backups/multimax_db_backup.7z /opt/multimax/backups/*.sql.gz
```

---

## 💾 Backup e Restore

### Backup Automático

```bash
# Agendar backup diário (via cron)
sudo crontab -e

# Adicionar linha:
0 2 * * * /usr/local/bin/multimax-db-backup.sh

# Backup também diretório app
0 3 * * * tar -czf /opt/multimax/backups/app_$(date +\%Y\%m\%d).tar.gz /opt/multimax/app
```

### Backup Manual

```bash
# BD completo
sudo multimax-db-backup.sh

# Verificar backup
ls -lh /opt/multimax/backups/
```

### Restaurar de Backup

```bash
# Listar backups disponíveis
ls -la /opt/multimax/backups/

# Restaurar BD
sudo multimax-db-restore.sh /opt/multimax/backups/multimax_db_20250115_120000.sql.gz
```

### Backup Externo (Recomendado)

```bash
# Rsync para servidor remoto
sudo rsync -avz /opt/multimax/backups/ usuario@backup-server:/backups/multimax/

# ou S3
aws s3 sync /opt/multimax/backups/ s3://meu-bucket/multimax-backups/
```

---

## 🆙 Atualização

### Atualizar Aplicação

```bash
# Automático (recomendado)
sudo multimax-update.sh

# Manual
cd /opt/multimax/app
sudo -u multimax git fetch origin
sudo -u multimax git pull origin main
source /opt/multimax/venv/bin/activate
pip install -r requirements.txt
flask db upgrade
deactivate
sudo systemctl restart multimax
```

### Atualizar Sistema Operacional

```bash
# Atualizar pacotes
sudo apt-get update
sudo apt-get upgrade -y

# Atualizar distribuição
sudo apt-get dist-upgrade -y

# Reiniciar se necessário
sudo reboot
```

### Atualizar PostgreSQL

```bash
# Backup antes de atualizar!
sudo multimax-db-backup.sh

# Atualizar
sudo apt-get install -y postgresql-upgrade-db-all

# Reiniciar
sudo systemctl restart postgresql
```

### Rollback (Reverter Atualização)

```bash
# Git
cd /opt/multimax/app
sudo -u multimax git log --oneline -10  # Ver histórico
sudo -u multimax git checkout <commit-id>

# Restaurar DB de backup
sudo multimax-db-restore.sh /opt/multimax/backups/multimax_db_BACKUP.sql.gz

# Reiniciar
sudo systemctl restart multimax
```

---

## 📞 Suporte e Documentação

### Recursos Oficiais

- 🐙 GitHub: [MultiMax Repository](https://github.com/SrLuther/MultiMax)
- 📖 Documentação: [MultiMax Docs](https://github.com/SrLuther/MultiMax/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/SrLuther/MultiMax/issues)

### Logs para Diagnóstico

Ao reportar problemas, inclua:

```bash
# Coletar informações
sudo journalctl -u multimax -n 100 > /tmp/multimax.log
sudo tail -100 /var/log/nginx/multimax_error.log >> /tmp/multimax.log
dpkg -l | grep -E "python|postgresql|nginx" >> /tmp/multimax.log
df -h >> /tmp/multimax.log
ps aux | grep python >> /tmp/multimax.log
```

Compartilhe `/tmp/multimax.log` (remova dados sensíveis antes).

---

## 📋 Checklist de Deploy

```
[ ] Servidor Ubuntu 24.04 LTS preparado
[ ] Python 3.11+ instalado
[ ] PostgreSQL instalado e rodando
[ ] Repositório clonado em /opt/multimax/app
[ ] Virtual environment criado
[ ] Dependências instaladas
[ ] Arquivo .env configurado com SECRET_KEY
[ ] Banco de dados inicializado (flask db upgrade)
[ ] Nginx configurado com domínio correto
[ ] Certificado SSL válido gerado
[ ] Systemd service habilitado
[ ] Aplicação inicia com sucesso
[ ] Teste de acesso via HTTPS
[ ] Firewall configurado
[ ] Backup automático configurado
[ ] Monitoramento em lugar
```

---

## 🎓 Próximas Etapas

1. **Configurar Monitoramento:** Sentry, New Relic ou similares
2. **Logs Centralizados:** ELK Stack ou Splunk
3. **CI/CD Pipeline:** GitHub Actions ou GitLab CI
4. **Load Balancing:** Nginx com múltiplas instâncias
5. **CDN:** CloudFlare para assets estáticos
6. **Database Replication:** PostgreSQL replicado para HA

---

**Última revisão:** Janeiro 2025  
**Mantido por:** [Seu Nome/Equipe]  
**Licença:** MIT
