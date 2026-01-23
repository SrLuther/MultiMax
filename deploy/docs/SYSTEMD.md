# MultiMax - Systemd Service Management

## Visão Geral

O arquivo `/etc/systemd/system/multimax.service` define como a aplicação é gerenciada pelo systemd (init system do Ubuntu).

---

## Arquivo de Serviço

**Localização:** `/etc/systemd/system/multimax.service`

```ini
[Unit]
Description=MultiMax Application Server
Documentation=file:///opt/multimax/docs/DEPLOYMENT.md
After=network.target postgresql.service

# Reiniciar automático em caso de falha
StartLimitBurst=5
StartLimitInterval=60s

[Service]
Type=simple
User=multimax
Group=multimax
WorkingDirectory=/opt/multimax

# Ambiente
EnvironmentFile=/opt/multimax/.env

# Execução
ExecStart=/opt/multimax/venv/bin/python /opt/multimax/app.py
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

# Restart policy
Restart=on-failure
RestartSec=10s

# Timeout
TimeoutStartSec=30s
TimeoutStopSec=10s

# Limites de recursos
LimitNOFILE=65535
LimitNPROC=512

# Segurança
PrivateTmp=yes
NoNewPrivileges=yes

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=multimax

[Install]
WantedBy=multi-user.target
```

---

## Componentes Explicados

### [Unit]

```ini
[Unit]
Description=MultiMax Application Server
Documentation=file:///opt/multimax/docs/DEPLOYMENT.md
After=network.target postgresql.service
```

- **Description**: Nome descritivo do serviço
- **Documentation**: Referência a documentação
- **After**: Iniciar após esses serviços (network, postgresql)

### [Service]

```ini
[Service]
Type=simple
User=multimax
Group=multimax
WorkingDirectory=/opt/multimax
EnvironmentFile=/opt/multimax/.env
```

- **Type=simple**: Processo em foreground (não daemonize)
- **User/Group**: Executar como usuário não-root
- **WorkingDirectory**: Diretório de execução
- **EnvironmentFile**: Carregar variáveis de `.env`

### Execução

```ini
ExecStart=/opt/multimax/venv/bin/python /opt/multimax/app.py
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
```

- **ExecStart**: Comando para iniciar
- **ExecReload**: Recarregar configuração (hot reload)
- **ExecStop**: Parar aplicação (gracefully)

### Restart

```ini
Restart=on-failure
RestartSec=10s
```

- **Restart=on-failure**: Reiniciar se sair com erro
- **RestartSec=10s**: Esperar 10s antes de reiniciar
- **StartLimitBurst=5, StartLimitInterval=60s**: Max 5 restarts em 60s

### Limites de Recursos

```ini
LimitNOFILE=65535      # Max file descriptors
LimitNPROC=512         # Max processos
```

---

## Operações Comuns

### Carregar e habilitar

```bash
# Após editar arquivo
sudo systemctl daemon-reload

# Habilitar auto-start na inicialização
sudo systemctl enable multimax
```

### Iniciar, parar, reiniciar

```bash
# Iniciar
sudo systemctl start multimax

# Parar
sudo systemctl stop multimax

# Reiniciar
sudo systemctl restart multimax

# Recarregar configuração (sem downtime)
sudo systemctl reload multimax
```

### Ver status

```bash
# Status completo
sudo systemctl status multimax

# Status simplificado
sudo systemctl is-active multimax

# Ver se habilitado na inicialização
sudo systemctl is-enabled multimax
```

### Logs

```bash
# Últimas linhas
sudo journalctl -u multimax -n 50

# Tempo real (follow)
sudo journalctl -u multimax -f

# Por período
sudo journalctl -u multimax --since "2026-01-23" --until "2026-01-24"

# Apenas erros
sudo journalctl -u multimax -p err

# Com prioridades
# 0=emerg, 1=alert, 2=crit, 3=err, 4=warning, 5=notice, 6=info, 7=debug
```

---

## Customizações Comuns

### Mudar porta

Editar `ExecStart`:
```ini
ExecStart=/opt/multimax/venv/bin/python /opt/multimax/app.py --port=8000
```

Ou via `.env`:
```env
MULTIMAX_PORT=8000
```

### Mudar usuário/grupo

```ini
[Service]
User=app
Group=app
```

Depois reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart multimax
```

### Habilitar hot reload

```ini
[Service]
ExecReload=/bin/kill -HUP $MAINPID
```

Depois:
```bash
sudo systemctl reload multimax
```

### Limitar memória

```ini
[Service]
MemoryLimit=512M
MemoryMax=1G
```

### Limitar CPU

```ini
[Service]
CPUQuota=50%       # Max 50% de um CPU
CPUShares=1024     # Relativo a outros serviços
```

### Executar script antes de iniciar

```ini
[Service]
ExecStartPre=/opt/multimax/deploy/scripts/db-manager.sh init
ExecStart=/opt/multimax/venv/bin/python /opt/multimax/app.py
```

### Executar script ao parar

```ini
[Service]
ExecStop=/opt/multimax/deploy/scripts/app-manager.sh stop
ExecStopPost=/opt/multimax/deploy/scripts/cleanup.sh
```

---

## Exemplos Avançados

### Multi-worker (Gunicorn)

```ini
[Service]
ExecStart=/opt/multimax/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=gevent \
    --bind=127.0.0.1:5000 \
    app:app
```

Instalar Gunicorn:
```bash
sudo -u multimax /opt/multimax/venv/bin/pip install gunicorn gevent
```

### Com health check

```ini
[Service]
ExecStartPost=/usr/bin/bash -c 'sleep 5 && curl -f http://localhost:5000/health || systemctl stop multimax'
```

### Depend de outro serviço

```ini
[Unit]
After=postgresql.service redis.service

[Service]
ExecStartPre=/usr/bin/bash -c 'until pg_isready; do sleep 1; done'
```

---

## Monitoramento

### Verificar saúde do serviço

```bash
# Status básico
sudo systemctl status multimax --lines=20 --no-pager

# Detalhes de tempo de atividade
sudo systemctl show multimax -p Result -p ExecStart

# Memory/CPU
ps aux | grep multimax | grep -v grep
```

### Health check endpoint

Adicione em sua app:
```python
@app.route('/health')
def health():
    return {'status': 'ok', 'version': '3.0.17'}, 200
```

Teste:
```bash
curl http://localhost:5000/health
```

### Monitoramento automático

```bash
# Adicionar ao cron (a cada 5 min)
*/5 * * * * curl -f http://localhost:5000/health || systemctl restart multimax
```

---

## Troubleshooting

### Serviço não inicia

```bash
# 1. Ver erro completo
sudo journalctl -u multimax -n 100

# 2. Testar comando manualmente
sudo -u multimax /opt/multimax/venv/bin/python /opt/multimax/app.py

# 3. Verificar permissões
ls -la /opt/multimax/.env
ls -la /opt/multimax/app.py
```

### Serviço para após poucos segundos

```bash
# 1. Verificar se aplicação tem erro
sudo -u multimax /opt/multimax/venv/bin/python /opt/multimax/app.py

# 2. Ver logs detalhados
sudo journalctl -u multimax -n 50

# 3. Aumentar TimeoutStartSec
# [Service]
# TimeoutStartSec=60s
```

### Serviço trava (hang)

```bash
# 1. Aumentar TimeoutStopSec
# [Service]
# TimeoutStopSec=30s

# 2. Forçar parada
sudo systemctl kill -s KILL multimax

# 3. Reset
sudo systemctl reset-failed multimax
```

### Muita latência/lento

```bash
# 1. Ver se reinicia constantemente
sudo journalctl -u multimax | grep "Restart"

# 2. Verificar limites
sudo systemctl show multimax -p LimitNOFILE LimitNPROC

# 3. Aumentar se necessário
# [Service]
# LimitNOFILE=65535
# LimitNPROC=1024
```

---

## Integração com Nginx

Garantir que Nginx inicia **após** MultiMax:

```bash
# Edit multimax.service
sudo systemctl edit multimax

# Adicionar na seção [Unit]
After=network.target postgresql.service
Before=nginx.service
```

Ou configurar nginx.service:
```ini
# /etc/systemd/system/nginx.service (adicionar)
[Unit]
After=multimax.service
```

---

## Teste de Failover

```bash
# Matar processo manualmente
sudo killall python

# Verificar que systemd reinicia
sleep 5
sudo systemctl status multimax

# Deve estar "active (running)" novamente
```

---

## Documentação Oficial

- [man systemd.service](https://man.archlinux.org/man/systemd.service.en)
- [man systemctl](https://man.archlinux.org/man/systemctl.1.en)
- [man journalctl](https://man.archlinux.org/man/journalctl.1.en)

---

**Última atualização:** 23 de janeiro de 2026  
**Systemd v252+** | **Ubuntu 24.04 LTS**
