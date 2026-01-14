# Deploy Agent - Sistema de Atualização Automática do MultiMax

## Visão Geral

O **Deploy Agent** é um serviço auxiliar que permite atualizar o MultiMax via interface web, sem acesso manual ao terminal, seguindo uma arquitetura segura e profissional.

## Arquitetura

```
┌─────────────────┐         HTTP POST          ┌─────────────────┐
│                 │    ───────────────────>    │                 │
│  MultiMax       │    http://127.0.0.1:9000   │  Deploy Agent   │
│  (Container)    │                            │  (HOST)         │
│                 │    <───────────────────    │                 │
│  - Interface    │         JSON Response      │  - Git          │
│  - Endpoint     │                            │  - Docker       │
│  - Sem comandos │                            │  - Execução     │
└─────────────────┘                            └─────────────────┘
```

### Separação de Responsabilidades

- **MultiMax (Container)**:
  - Interface web (`/db`)
  - Endpoint `/git/update` que faz apenas requisições HTTP
  - **NÃO executa** comandos Git ou Docker
  - **NÃO acessa** o diretório `.git`

- **Deploy Agent (HOST)**:
  - Serviço Flask escutando em `127.0.0.1:9000`
  - Executa comandos Git e Docker no HOST
  - Aceita apenas conexões localhost
  - Executa sequência fixa e controlada de comandos

## Fluxo de Atualização

1. **Admin acessa** `https://multimax.tec.br/db`
2. **Card "Monitoramento de Atualizações Git"** mostra status e botão "Aplicar Atualização"
3. **Admin clica** no botão e confirma
4. **MultiMax (container)** faz `POST http://127.0.0.1:9000/deploy` com `{"force": false}`
5. **Deploy Agent (HOST)** executa sequência fixa:
   ```bash
   cd /opt/multimax
   git fetch origin
   git reset --hard origin/nova-versao-deploy
   docker-compose build --no-cache
   docker-compose down
   docker-compose up -d
   ```
6. **Deploy Agent** retorna status e logs
7. **MultiMax** exibe feedback ao usuário
8. **Sistema reinicia** automaticamente após ~5 minutos

## Segurança

### Implementado

✅ **Apenas localhost**: Deploy Agent aceita apenas `127.0.0.1`  
✅ **Token opcional**: Suporte para `DEPLOY_AGENT_TOKEN`  
✅ **Comandos fixos**: Não aceita comandos arbitrários  
✅ **Validação de origem**: Verifica IP de origem  
✅ **Sem exposição externa**: Porta 9000 não exposta externamente  

### Recomendações

1. **Firewall**: Bloquear porta 9000 externamente
   ```bash
   sudo ufw deny 9000
   ```

2. **Token**: Configurar `DEPLOY_AGENT_TOKEN` para camada extra de segurança

3. **Monitoramento**: Acompanhar logs regularmente

## Instalação Rápida

```bash
# 1. Copiar arquivo
sudo cp deploy_agent.py /opt/multimax/
sudo chmod +x /opt/multimax/deploy_agent.py

# 2. Instalar dependências
pip3 install flask

# 3. Criar serviço systemd (veja DEPLOY_AGENT_INSTALL.md)

# 4. Habilitar e iniciar
sudo systemctl enable deploy-agent
sudo systemctl start deploy-agent

# 5. Verificar
curl http://127.0.0.1:9000/health
```

**Para instruções detalhadas, veja:** [DEPLOY_AGENT_INSTALL.md](DEPLOY_AGENT_INSTALL.md)

## Endpoints do Deploy Agent

### `GET /health`

Health check do serviço.

**Resposta:**
```json
{
  "ok": true,
  "service": "deploy-agent",
  "version": "1.0.0",
  "repo_dir": "/opt/multimax",
  "timestamp": "2025-01-15T10:30:00"
}
```

### `POST /deploy`

Inicia o processo de deploy.

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>  # Opcional, se DEPLOY_AGENT_TOKEN configurado
```

**Body:**
```json
{
  "force": false  // Se true, força atualização mesmo se já estiver atualizado
}
```

**Resposta de Sucesso:**
```json
{
  "ok": true,
  "message": "Deploy concluído com sucesso",
  "results": [
    {
      "success": true,
      "description": "Fetch do repositório remoto",
      "duration": 2.5,
      "returncode": 0
    },
    // ... outros comandos
  ],
  "duration": 450.2,
  "timestamp": "2025-01-15T10:35:00"
}
```

**Resposta de Erro:**
```json
{
  "ok": false,
  "error": "Erro ao executar: Rebuild completo do container",
  "details": "STDERR: ...",
  "failed_step": "Rebuild completo do container (sem cache)",
  "results": [
    // ... comandos executados até o erro
  ],
  "duration": 120.5
}
```

### `GET /status`

Retorna status atual do Deploy Agent e repositório.

**Resposta:**
```json
{
  "ok": true,
  "service": "deploy-agent",
  "repo_dir": "/opt/multimax",
  "repo_exists": true,
  "git_exists": true,
  "current_commit": "abc123def456...",
  "timestamp": "2025-01-15T10:30:00"
}
```

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GIT_REPO_DIR` | `/opt/multimax` | Diretório do repositório Git |
| `DEPLOY_AGENT_PORT` | `9000` | Porta do Deploy Agent |
| `DEPLOY_AGENT_TOKEN` | `""` | Token de autenticação (opcional) |

## Logs

### Deploy Agent

```bash
# Ver logs em tempo real
sudo journalctl -u deploy-agent -f

# Últimos 100 linhas
sudo journalctl -u deploy-agent -n 100

# Logs desde hoje
sudo journalctl -u deploy-agent --since today
```

Os logs também são salvos em `/var/log/deploy-agent.log`.

### MultiMax

```bash
# Logs do container
docker-compose logs -f multimax

# Filtrar logs de atualização
docker-compose logs multimax | grep -i "deploy\|git\|update"
```

## Solução de Problemas Comuns

### "Não foi possível conectar ao Deploy Agent"

**Sintoma:** Erro 503 ao tentar atualizar

**Soluções:**
1. Verificar se o serviço está rodando:
   ```bash
   sudo systemctl status deploy-agent
   ```

2. Verificar se está escutando na porta 9000:
   ```bash
   netstat -tlnp | grep 9000
   ```

3. Verificar variável de ambiente no container:
   ```bash
   docker-compose exec multimax env | grep DEPLOY_AGENT
   ```

4. Verificar logs do Deploy Agent:
   ```bash
   sudo journalctl -u deploy-agent -n 50
   ```

### "Timeout ao aguardar resposta"

**Sintoma:** Erro 504 após 15 minutos

**Soluções:**
1. Build do Docker pode estar demorando mais que o esperado
2. Verificar logs do Deploy Agent para ver em qual etapa parou
3. Aumentar timeout no `deploy_agent.py` se necessário

### "Token de autenticação inválido"

**Sintoma:** Erro 401

**Soluções:**
1. Verificar se `DEPLOY_AGENT_TOKEN` está configurado igual no Deploy Agent e no container
2. Verificar header `Authorization: Bearer <token>` na requisição
3. Se não usar token, remover `DEPLOY_AGENT_TOKEN` de ambos os lugares

## Desenvolvimento

### Testar Manualmente

```bash
# Iniciar Deploy Agent manualmente
cd /opt/multimax
python3 deploy_agent.py

# Em outro terminal, testar health check
curl http://127.0.0.1:9000/health

# Testar deploy (cuidado: vai executar comandos reais!)
curl -X POST http://127.0.0.1:9000/deploy \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

### Modificar Comandos

Para alterar a sequência de comandos, edite a função `deploy()` em `deploy_agent.py`:

```python
commands = [
    (['git', 'fetch', 'origin'], 'Descrição', timeout),
    # ... outros comandos
]
```

**Importante:** Sempre teste em ambiente de desenvolvimento primeiro!

## Manutenção

### Atualizar Deploy Agent

```bash
# Fazer backup
sudo cp /opt/multimax/deploy_agent.py /opt/multimax/deploy_agent.py.backup

# Copiar nova versão
sudo cp deploy_agent.py /opt/multimax/

# Reiniciar serviço
sudo systemctl restart deploy-agent

# Verificar
curl http://127.0.0.1:9000/health
```

### Reiniciar Serviço

```bash
sudo systemctl restart deploy-agent
```

### Parar Serviço

```bash
sudo systemctl stop deploy-agent
```

## Suporte

Para problemas ou dúvidas:
- Verifique os logs: `sudo journalctl -u deploy-agent -f`
- Consulte [DEPLOY_AGENT_INSTALL.md](DEPLOY_AGENT_INSTALL.md)
- Revise o código: `deploy_agent.py` (bem documentado)
