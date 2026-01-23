# 🔧 Troubleshooting e FAQ

> Soluções para problemas comuns

## Índice

1. [Não inicia](#não-inicia)
2. [Erro de conexão](#erro-de-conexão)
3. [Slow/Timeout](#slowtimeout)
4. [Erro de permissão](#erro-de-permissão)
5. [SSL/HTTPS](#ssltls)
6. [Database](#database)
7. [Memory/CPU](#memorycpu)
8. [FAQ](#faq)

---

## ❌ Não Inicia

### Erro: "Service failed to start"

```bash
# Ver erro completo
sudo journalctl -u multimax -n 100 -p err

# Tentar em foreground
cd /opt/multimax/app
source /opt/multimax/venv/bin/activate
python app.py
# Ctrl+C para parar
```

### Erro: "ModuleNotFoundError"

```bash
# Verificar venv
which python
# Deve ser: /opt/multimax/venv/bin/python

# Reinstalar dependências
source /opt/multimax/venv/bin/activate
pip install -r /opt/multimax/app/requirements.txt
```

### Erro: "Address already in use"

```bash
# Encontrar processo na porta 5000
sudo lsof -i :5000
# ou
sudo netstat -tlnp | grep 5000

# Matar processo
sudo kill -9 <PID>

# Reiniciar
sudo systemctl restart multimax
```

---

## 🔗 Erro de Conexão

### Nginx retorna 502 Bad Gateway

**Causa:** Flask não está respondendo

```bash
# 1. Verificar se Flask roda
sudo systemctl status multimax

# 2. Testar conexão
curl http://127.0.0.1:5000/health

# 3. Ver logs Flask
sudo tail -50 /var/log/multimax/app.log

# 4. Ver logs Nginx
sudo tail -50 /var/log/nginx/multimax_error.log

# 5. Reiniciar tudo
sudo systemctl restart multimax nginx
```

### "Connection refused" no banco

**Causa:** PostgreSQL não está rodando ou não acessível

```bash
# 1. Verificar PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# 2. Testar conexão
psql -U multimax -d multimax -h localhost

# 3. Verificar DATABASE_URL
grep DATABASE_URL /opt/multimax/.env

# 4. Reiniciar multimax
sudo systemctl restart multimax
```

### "Host is down"

**Causa:** Rede/Firewall bloqueando

```bash
# 1. Verificar conectividade
ping seu-dominio.com

# 2. Testar porta
telnet seu-dominio.com 443

# 3. Verificar firewall
sudo ufw status

# 4. Permitir porta se necessário
sudo ufw allow 443/tcp
```

---

## 🐢 Slow/Timeout

### Requisição lenta (> 10 segundos)

**Causa:** CPU/Memoria alta ou Query BD lenta

```bash
# 1. Ver recursos
top -bn1 | head -20

# 2. Verificar queries lentes
sudo -u postgres psql -d multimax -c "
SELECT pid, usename, query, query_start 
FROM pg_stat_activity 
WHERE state != 'idle';"

# 3. Ver logs de query lenta (postgresql.conf)
sudo tail -100 /var/log/postgresql/postgresql.log | grep 'duration:'

# 4. Adicionar índice se necessário
EXPLAIN ANALYZE SELECT ...;
```

### Timeout em upload

**Causa:** Arquivo muito grande ou network lenta

```bash
# 1. Aumentar timeouts em nginx
sudo nano /etc/nginx/sites-available/multimax

# Adicionar em server block:
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;

# 2. Aumentar em .env
sudo nano /opt/multimax/.env
REQUEST_TIMEOUT=300

# 3. Reiniciar
sudo systemctl restart nginx multimax
```

---

## 🚫 Erro de Permissão

### "Permission denied" ao salvar

```bash
# Ver proprietário
ls -la /opt/multimax/

# Corrigir
sudo chown -R multimax:multimax /opt/multimax
sudo chmod 750 /opt/multimax

# Logs
sudo chown -R multimax:multimax /var/log/multimax
sudo chmod 755 /var/log/multimax
```

### "Cannot create directory"

```bash
# Ver permissões da pasta
ls -ld /opt/multimax/uploads

# Corrigir
sudo mkdir -p /opt/multimax/uploads
sudo chown multimax:multimax /opt/multimax/uploads
sudo chmod 755 /opt/multimax/uploads
```

---

## 🔒 SSL/TLS

### "SSL certificate problem"

**Causa:** Certificado inválido ou expirado

```bash
# 1. Verificar validade
sudo certbot certificates

# 2. Renovar manualmente
sudo certbot renew --force-renewal

# 3. Verificar arquivo
openssl x509 -in /etc/letsencrypt/live/seu-dominio/cert.pem -text

# 4. Reiniciar Nginx
sudo systemctl restart nginx
```

### "Certificate not trusted"

**Causa:** CA não é confiável

```bash
# 1. Verificar cadeia
openssl s_client -connect seu-dominio.com:443 -showcerts

# 2. Verificar chain.pem
openssl x509 -in /etc/letsencrypt/live/seu-dominio/chain.pem -text

# 3. Usar fullchain.pem em Nginx
sudo nano /etc/nginx/sites-available/multimax

# Alterar:
ssl_certificate /etc/letsencrypt/live/seu-dominio/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/seu-dominio/privkey.pem;
```

### "Mixed content" (HTTP em HTTPS)

**Causa:** Recursos carregando via HTTP

```bash
# 1. Ver erro no browser console
# F12 -> Console -> procurar "mixed"

# 2. Verificar templates
grep -r "http://" /opt/multimax/app/templates/

# 3. Mudar para https://
sed -i 's|http://|https://|g' /opt/multimax/app/templates/*.html

# 4. Ou usar protocolo relativo:
# <img src="//cdn.example.com/...">
```

---

## 🗄️ Database

### "ERROR: database "multimax" already exists"

```bash
# Dropar BD existente (ATENÇÃO: perde dados!)
sudo -u postgres dropdb multimax

# Recriar
sudo -u postgres createdb multimax OWNER multimax

# Reinicializar
cd /opt/multimax/app
FLASK_APP=app.py flask db upgrade
```

### "FATAL: role "multimax" does not exist"

```bash
# Verificar usuários
sudo -u postgres psql -c "\du"

# Criar usuário
sudo -u postgres psql -c \
"CREATE USER multimax WITH PASSWORD 'senha123';"

# Ou atualizar senha
sudo -u postgres psql -c \
"ALTER USER multimax WITH PASSWORD 'nova-senha';"
```

### "could not connect to server"

```bash
# 1. Verificar se PostgreSQL roda
sudo systemctl status postgresql

# 2. Verificar arquivo de config
sudo nano /etc/postgresql/15/main/postgresql.conf

# Deve ter: listen_addresses = 'localhost'

# 3. Reiniciar
sudo systemctl restart postgresql

# 4. Testar conexão
psql -U multimax -d multimax -h localhost
```

### Database bloqueado

```bash
# Ver conexões ativas
sudo -u postgres psql -d multimax -c \
"SELECT * FROM pg_stat_activity WHERE datname='multimax';"

# Terminar conexão
sudo -u postgres psql -c \
"SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname='multimax' AND usename='multimax';"

# Ou restart forcado
sudo systemctl restart postgresql
```

---

## 💾 Memory/CPU

### Memory leak (crescimento contínuo)

**Causa:** Aplicação não liberando memória

```bash
# 1. Monitorar memória
watch -n 5 'ps aux | grep python'

# 2. Limitar em systemd
sudo nano /etc/systemd/system/multimax.service

# Adicionar:
MemoryMax=512M

# 3. Recarregar
sudo systemctl daemon-reload
sudo systemctl restart multimax

# 4. Procurar leak no código
pip install memory-profiler
python -m memory_profiler app.py
```

### CPU 100% constante

**Causa:** Loop infinito ou muita concorrência

```bash
# 1. Identificar qual thread usa CPU
top -H -p $(pgrep -f 'python.*app')

# 2. Traceback
sudo gdb -p $(pgrep -f 'python.*app')
> py-bt  # Stack trace Python

# 3. Aumentar workers se necessário
# Nas systemd/WSGI config: workers = num_cores * 2 + 1

# 4. Se BD:
sudo -u postgres psql -c "
SELECT pid, usename, query, state FROM pg_stat_activity 
WHERE state != 'idle';"
```

### Disco cheio

```bash
# 1. Ver uso
du -sh /opt/multimax/* | sort -h

# 2. Limpiar backups antigos
find /opt/multimax/backups -mtime +30 -delete

# 3. Limpar cache/tmp
sudo -u multimax rm -rf /opt/multimax/tmp/*

# 4. Limpar logs antigos
sudo journalctl --vacuum=time=30d

# 5. PostgreSQL cleanup
sudo -u postgres vacuumdb --analyze multimax
```

---

## ❓ FAQ

### P: Como atualizar Python?
**R:**
```bash
# 1. Backup
sudo multimax-db-backup.sh

# 2. Instalar nova versão
sudo apt-get install -y python3.12 python3.12-venv

# 3. Recriar venv
sudo -u multimax python3.12 -m venv /opt/multimax/venv-new

# 4. Instalar dependências
source /opt/multimax/venv-new/bin/activate
pip install -r /opt/multimax/app/requirements.txt

# 5. Testar
python --version

# 6. Trocar symlink
sudo mv /opt/multimax/venv /opt/multimax/venv-old
sudo mv /opt/multimax/venv-new /opt/multimax/venv

# 7. Reiniciar
sudo systemctl restart multimax
```

### P: Como resetar a aplicação?
**R:**
```bash
# ATENÇÃO: Isto apaga dados!
sudo systemctl stop multimax

# Reset BD
sudo -u postgres dropdb multimax
sudo -u postgres createdb multimax OWNER multimax

# Reset código
cd /opt/multimax/app && sudo -u multimax git reset --hard HEAD

# Reinicializar
cd /opt/multimax/app && FLASK_APP=app.py flask db upgrade

# Restart
sudo systemctl start multimax
```

### P: Como fazer restore de backup?
**R:**
```bash
# 1. Parar app
sudo systemctl stop multimax

# 2. Restaurar
sudo gunzip -c /opt/multimax/backups/multimax_db_20250115.sql.gz | \
  sudo -u postgres psql multimax

# 3. Reiniciar
sudo systemctl start multimax
```

### P: Como adicionar usuário admin?
**R:**
```bash
# No shell Python
cd /opt/multimax/app
source /opt/multimax/venv/bin/activate
python

# Dentro do Python:
from multimax.models import User
from multimax import create_app, db

app = create_app()
with app.app_context():
    user = User(email='admin@example.com', is_admin=True)
    user.set_password('senha123')
    db.session.add(user)
    db.session.commit()
    print('Admin criado!')
```

### P: Como desabilitar manutenção?
**R:**
```bash
# Remover arquivo de manutenção
sudo rm /opt/multimax/.maintenance

# Ou reiniciar
sudo systemctl restart multimax
```

### P: Como ver logs em tempo real?
**R:**
```bash
# Systemd
sudo journalctl -u multimax -f

# Ou arquivo
tail -f /var/log/multimax/app.log

# Filtrar por nível
sudo journalctl -u multimax -p err -f
```

### P: Como otimizar BD?
**R:**
```bash
# Reindex
sudo -u postgres reindexdb multimax

# Analyze
sudo -u postgres analyzedb multimax

# Vacuum full (lento, usar offline)
sudo -u postgres vacuumdb --full --analyze multimax

# Ver tamanho
sudo -u postgres psql -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

**Última revisão:** Janeiro 2025
