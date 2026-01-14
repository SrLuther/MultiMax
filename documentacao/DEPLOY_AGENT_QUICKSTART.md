# Deploy Agent - Guia Rápido de Instalação

## ⚡ Instalação Rápida (5 minutos)

### Pré-requisitos

- Acesso SSH ao servidor (HOST, não dentro do Docker)
- Permissões sudo
- Python 3.8+ instalado no HOST

### Passo a Passo

```bash
# 1. Acesse o servidor via SSH
ssh usuario@multimax.tec.br

# 2. Copie o arquivo deploy_agent.py para /opt/multimax/
cd /opt/multimax
# (Se o arquivo ainda não estiver no servidor, copie via scp ou git clone)

# 3. Torne o arquivo executável
sudo chmod +x /opt/multimax/deploy_agent.py

# 4. Instale Flask (se ainda não tiver)
pip3 install flask
# Ou, se preferir venv:
# python3 -m venv /opt/multimax/deploy_agent_venv
# source /opt/multimax/deploy_agent_venv/bin/activate
# pip install flask

# 5. Crie o arquivo de serviço systemd
sudo nano /etc/systemd/system/deploy-agent.service
```

Cole o seguinte conteúdo no arquivo:

```ini
[Unit]
Description=MultiMax Deploy Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/multimax
Environment="GIT_REPO_DIR=/opt/multimax"
Environment="DEPLOY_AGENT_PORT=9000"
# Opcional: Descomente se quiser usar token de segurança
# Environment="DEPLOY_AGENT_TOKEN=seu-token-secreto-aqui"
ExecStart=/usr/bin/python3 /opt/multimax/deploy_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Se usar ambiente virtual, altere `ExecStart` para:**
```ini
ExecStart=/opt/multimax/deploy_agent_venv/bin/python /opt/multimax/deploy_agent.py
```

```bash
# 6. Salve o arquivo (Ctrl+X, Y, Enter no nano)

# 7. Recarregue o systemd
sudo systemctl daemon-reload

# 8. Habilite o serviço (inicia automaticamente no boot)
sudo systemctl enable deploy-agent

# 9. Inicie o serviço
sudo systemctl start deploy-agent

# 10. Verifique se está rodando
sudo systemctl status deploy-agent

# 11. Teste o health check
curl http://127.0.0.1:9000/health
```

**Deve retornar:**
```json
{
  "ok": true,
  "service": "deploy-agent",
  "version": "1.0.0",
  "repo_dir": "/opt/multimax",
  "timestamp": "2025-01-15T..."
}
```

### Configurar Variável de Ambiente no Container MultiMax

```bash
# Edite o docker-compose.yml
cd /opt/multimax
nano docker-compose.yml
```

Adicione na seção `environment` do serviço `multimax`:

```yaml
services:
  multimax:
    environment:
      - DEPLOY_AGENT_URL=http://127.0.0.1:9000
      # Opcional, se configurou token no Deploy Agent:
      # - DEPLOY_AGENT_TOKEN=seu-token-secreto-aqui
```

```bash
# Reinicie o container
docker-compose restart multimax
```

## ✅ Verificação Final

```bash
# 1. Verificar se o serviço está rodando
sudo systemctl status deploy-agent

# 2. Verificar se está escutando na porta 9000
netstat -tlnp | grep 9000
# Deve mostrar algo como: tcp 0 0 127.0.0.1:9000 0.0.0.0:* LISTEN

# 3. Testar health check
curl http://127.0.0.1:9000/health

# 4. Testar do container (se estiver usando network_mode: host)
docker-compose exec multimax curl http://127.0.0.1:9000/health
```

## 🐛 Solução de Problemas

### Serviço não inicia

```bash
# Ver logs detalhados
sudo journalctl -u deploy-agent -n 50

# Verificar permissões
ls -la /opt/multimax/deploy_agent.py

# Testar manualmente
cd /opt/multimax
python3 deploy_agent.py
# (Deve iniciar e escutar em 127.0.0.1:9000)
```

### Porta 9000 não está acessível

```bash
# Verificar se está escutando
netstat -tlnp | grep 9000

# Verificar firewall
sudo ufw status

# Verificar se outro processo está usando a porta
sudo lsof -i :9000
```

### Erro de conexão do container para o HOST

Se o container não conseguir acessar `127.0.0.1:9000`, você tem 3 opções:

**OPÇÃO 1: Usar network_mode: host (Recomendado)**

Edite `docker-compose.yml`:

```yaml
services:
  multimax:
    network_mode: host
    # ... outras configurações ...
```

**OPÇÃO 2: Usar host.docker.internal (Docker Desktop/WSL)**

No `docker-compose.yml`:

```yaml
services:
  multimax:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - DEPLOY_AGENT_URL=http://host.docker.internal:9000
```

**OPÇÃO 3: Usar IP do HOST (menos seguro)**

Descubra o IP do HOST:
```bash
hostname -I | awk '{print $1}'
```

Use no `docker-compose.yml`:
```yaml
services:
  multimax:
    environment:
      - DEPLOY_AGENT_URL=http://172.17.0.1:9000  # Substitua pelo IP real
```

## 📚 Documentação Completa

Para mais detalhes, consulte:
- **DEPLOY_AGENT_INSTALL.md** - Instalação detalhada passo a passo
- **DEPLOY_AGENT_README.md** - Documentação completa do sistema

## 🆘 Suporte

Se ainda tiver problemas:

1. Verifique os logs: `sudo journalctl -u deploy-agent -f`
2. Verifique os logs do MultiMax: `docker-compose logs -f multimax`
3. Consulte DEPLOY_AGENT_INSTALL.md para troubleshooting detalhado
