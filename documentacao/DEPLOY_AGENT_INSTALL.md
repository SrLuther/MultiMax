# Instalação do Deploy Agent - Sistema de Atualização Automática

## Visão Geral

O **Deploy Agent** é um serviço auxiliar que roda diretamente no HOST (fora do Docker) e é responsável por executar comandos Git e Docker durante as atualizações do MultiMax.

**Arquitetura:**
- **MultiMax (container)**: Faz requisições HTTP para `http://127.0.0.1:9000/deploy`
- **Deploy Agent (HOST)**: Executa comandos Git/Docker no HOST, fora do container

## Requisitos

- Python 3.8 ou superior
- Flask instalado (`pip install flask`)
- Acesso ao diretório `/opt/multimax` (ou outro configurado)
- Permissões para executar `git` e `docker-compose`
- Usuário com permissões sudo (para instalar como serviço systemd)

## Instalação Passo a Passo

### 1. Copiar o Deploy Agent para o HOST

```bash
# No HOST (fora do Docker)
sudo cp deploy_agent.py /opt/multimax/deploy_agent.py
sudo chmod +x /opt/multimax/deploy_agent.py
```

### 2. Instalar Dependências Python

```bash
# No HOST
pip3 install flask
# Ou, se preferir ambiente virtual:
python3 -m venv /opt/multimax/deploy_agent_venv
source /opt/multimax/deploy_agent_venv/bin/activate
pip install flask
```

### 3. Configurar Variáveis de Ambiente (Opcional)

Edite `/opt/multimax/deploy_agent.py` ou crie um arquivo de configuração:

```bash
# Opcional: Configurar token de segurança
export DEPLOY_AGENT_TOKEN="seu-token-secreto-aqui"

# Opcional: Configurar diretório do repositório (padrão: /opt/multimax)
export GIT_REPO_DIR="/opt/multimax"

# Opcional: Configurar porta (padrão: 9000)
export DEPLOY_AGENT_PORT="9000"
```

**Importante:** Se configurar `DEPLOY_AGENT_TOKEN`, você também deve configurar a mesma variável no container do MultiMax (via `docker-compose.yml` ou `.env`).

### 4. Criar Serviço systemd

Crie o arquivo `/etc/systemd/system/deploy-agent.service`:

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
# Opcional: Descomente e configure se usar token
# Environment="DEPLOY_AGENT_TOKEN=seu-token-secreto-aqui"
ExecStart=/usr/bin/python3 /opt/multimax/deploy_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Nota:** Se usar ambiente virtual, ajuste `ExecStart`:

```ini
ExecStart=/opt/multimax/deploy_agent_venv/bin/python /opt/multimax/deploy_agent.py
```

### 5. Habilitar e Iniciar o Serviço

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar serviço (inicia automaticamente no boot)
sudo systemctl enable deploy-agent

# Iniciar serviço
sudo systemctl start deploy-agent

# Verificar status
sudo systemctl status deploy-agent

# Ver logs em tempo real
sudo journalctl -u deploy-agent -f
```

### 6. Verificar que o Serviço Está Rodando

```bash
# Verificar se está escutando na porta 9000
netstat -tlnp | grep 9000
# Ou
ss -tlnp | grep 9000

# Testar endpoint de health check
curl http://127.0.0.1:9000/health
```

Deve retornar algo como:
```json
{
  "ok": true,
  "service": "deploy-agent",
  "version": "1.0.0",
  "repo_dir": "/opt/multimax",
  "timestamp": "2025-01-XX..."
}
```

### 7. Configurar Variáveis de Ambiente no Container MultiMax

Edite o `docker-compose.yml` e adicione as variáveis de ambiente:

```yaml
services:
  multimax:
    # ... outras configurações ...
    environment:
      - DEPLOY_AGENT_URL=http://127.0.0.1:9000
      # Opcional: Se configurou token no Deploy Agent, descomente:
      # - DEPLOY_AGENT_TOKEN=seu-token-secreto-aqui
```

**Importante:** O container deve poder acessar `127.0.0.1:9000` do HOST. Se estiver usando `network_mode: host` no docker-compose, já funcionará. Caso contrário, você pode precisar ajustar as configurações de rede.

### 8. Reiniciar o Container MultiMax

```bash
cd /opt/multimax
docker-compose restart multimax
```

### 9. Testar a Integração

1. Acesse `https://multimax.tec.br/db` como desenvolvedor
2. Verifique o card "Monitoramento de Atualizações Git"
3. Se houver atualização disponível, clique em "Aplicar Atualização Completa"
4. Acompanhe os logs do Deploy Agent:

```bash
sudo journalctl -u deploy-agent -f
```

## Segurança

### Validações Implementadas

1. **Apenas localhost**: O Deploy Agent aceita apenas conexões de `127.0.0.1` (localhost)
2. **Token opcional**: Pode configurar `DEPLOY_AGENT_TOKEN` para autenticação adicional
3. **Comandos fixos**: O Deploy Agent executa apenas uma sequência fixa de comandos, não aceita comandos arbitrários
4. **Sem exposição externa**: A porta 9000 não deve ser exposta externamente (firewall)

### Recomendações de Segurança

1. **Firewall**: Certifique-se de que a porta 9000 não esteja acessível externamente:
   ```bash
   sudo ufw deny 9000
   # Ou no firewall do seu provedor
   ```

2. **Token**: Configure `DEPLOY_AGENT_TOKEN` para adicionar uma camada extra de segurança

3. **Permissões**: Execute o Deploy Agent como usuário apropriado (root pode ser necessário para docker-compose)

4. **Logs**: Monitore os logs regularmente:
   ```bash
   sudo journalctl -u deploy-agent -n 100
   ```

## Solução de Problemas

### Serviço não inicia

```bash
# Verificar logs detalhados
sudo journalctl -u deploy-agent -n 50

# Verificar permissões
ls -la /opt/multimax/deploy_agent.py

# Testar manualmente
cd /opt/multimax
python3 deploy_agent.py
```

### Erro de conexão do MultiMax

```bash
# Verificar se o serviço está rodando
sudo systemctl status deploy-agent

# Verificar se está escutando
netstat -tlnp | grep 9000

# Verificar variável de ambiente no container
docker-compose exec multimax env | grep DEPLOY_AGENT

# Testar conectividade do container para o HOST
docker-compose exec multimax curl http://127.0.0.1:9000/health
```

**Nota:** Se o container não conseguir acessar `127.0.0.1:9000`, pode ser necessário:
- Usar `network_mode: host` no docker-compose.yml
- Ou usar o IP do HOST em vez de `127.0.0.1` (menos seguro)

### Erro ao executar comandos Git/Docker

```bash
# Verificar permissões
cd /opt/multimax
ls -la .git

# Verificar se docker-compose está acessível
which docker-compose
docker-compose --version

# Verificar se git está acessível
which git
git --version

# Testar comandos manualmente
cd /opt/multimax
git fetch origin
docker-compose --version
```

### Timeout durante deploy

O timeout padrão é de 15 minutos. Se o build do Docker estiver demorando mais:

1. Edite `/opt/multimax/deploy_agent.py` e aumente o timeout na linha:
   ```python
   timeout=900  # 15 minutos em segundos
   ```

2. Reinicie o serviço:
   ```bash
   sudo systemctl restart deploy-agent
   ```

## Manutenção

### Parar o Serviço

```bash
sudo systemctl stop deploy-agent
```

### Reiniciar o Serviço

```bash
sudo systemctl restart deploy-agent
```

### Desabilitar o Serviço (não inicia no boot)

```bash
sudo systemctl disable deploy-agent
```

### Ver Logs

```bash
# Últimos 100 linhas
sudo journalctl -u deploy-agent -n 100

# Seguir logs em tempo real
sudo journalctl -u deploy-agent -f

# Logs desde hoje
sudo journalctl -u deploy-agent --since today

# Logs entre datas
sudo journalctl -u deploy-agent --since "2025-01-15" --until "2025-01-16"
```

### Atualizar o Deploy Agent

```bash
# 1. Fazer backup do arquivo atual
sudo cp /opt/multimax/deploy_agent.py /opt/multimax/deploy_agent.py.backup

# 2. Copiar nova versão
sudo cp deploy_agent.py /opt/multimax/deploy_agent.py

# 3. Reiniciar serviço
sudo systemctl restart deploy-agent

# 4. Verificar se está funcionando
curl http://127.0.0.1:9000/health
sudo journalctl -u deploy-agent -n 20
```

## Desinstalação

Se precisar remover o Deploy Agent:

```bash
# 1. Parar e desabilitar serviço
sudo systemctl stop deploy-agent
sudo systemctl disable deploy-agent

# 2. Remover arquivo do systemd
sudo rm /etc/systemd/system/deploy-agent.service

# 3. Recarregar systemd
sudo systemctl daemon-reload

# 4. Remover arquivo (opcional)
sudo rm /opt/multimax/deploy_agent.py
```

## Suporte

Para problemas ou dúvidas, verifique:
- Logs do Deploy Agent: `sudo journalctl -u deploy-agent -f`
- Logs do MultiMax: `docker-compose logs -f multimax`
- Documentação no código: `deploy_agent.py`
