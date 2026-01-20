# Guia de Deployment da VPS - MultiMax

Data: 20 de janeiro de 2026  
Versão: 2.6.71  
Branch: `nova-versao-deploy`

---

## 📋 Pré-requisitos

Antes de executar o deployment, verifique:

```bash
# Conectar via SSH
ssh usuario@seu-servidor-vps

# Verificar se está no diretório correto
cd /opt/multimax && pwd

# Verificar git está instalado
git --version

# Verificar Docker está rodando
docker --version && docker-compose --version

# Verificar permissões sudo
sudo -l | grep systemctl
```

---

## 🚀 Procedimento Principal de Deployment

### **1. Sincronizar com GitHub**

```bash
cd /opt/multimax
git fetch origin
git reset --hard origin/nova-versao-deploy
```

**O que faz:**
- `git fetch origin` → Busca as mudanças do repositório remoto
- `git reset --hard origin/nova-versao-deploy` → Força o repositório local para corresponder exatamente ao remoto (descarta mudanças locais)

---

### **2. Reconstruir imagem Docker**

```bash
docker-compose build --no-cache
```

**O que faz:**
- `--no-cache` → Força rebuild completo (não usa cache, obtém dependências frescas)

**⚠️ Importante:** Este comando pode levar 5-15 minutos. Não cancele no meio.

---

### **3. Reiniciar serviços**

```bash
docker-compose down
docker-compose up -d
```

**O que faz:**
- `docker-compose down` → Para e remove containers
- `docker-compose up -d` → Inicia containers em background (`-d` = detached mode)

**Verificar se subiu corretamente:**
```bash
docker-compose ps
```

---

### **4. Recarregar configurações systemd e Deploy Agent**

```bash
sudo systemctl daemon-reload
sudo systemctl enable deploy-agent
sudo systemctl start deploy-agent
```

**O que faz:**
- `daemon-reload` → Recarrega configurações de serviços systemd
- `enable deploy-agent` → Define serviço para iniciar automaticamente no boot
- `start deploy-agent` → Inicia o serviço agora

**Verificar status:**
```bash
sudo systemctl status deploy-agent
```

---

## ✅ Verificações Pós-Deployment

Execute esses comandos para confirmar que tudo está funcionando:

```bash
# 1. Verificar containers rodando
docker-compose ps

# 2. Verificar logs da aplicação
docker-compose logs -f app

# 3. Verificar health check
curl http://localhost:5000/health

# 4. Verificar versão da aplicação
curl http://localhost:5000/api/version

# 5. Verificar Deploy Agent
sudo systemctl status deploy-agent

# 6. Verificar porta 9000 (Deploy Agent)
netstat -tlnp | grep 9000
# ou
ss -tlnp | grep 9000

# 7. Ver recursos utilizados
docker stats
```

---

## 🔧 Comandos Úteis Secundários

### **Monitoramento e Logs**

```bash
# Logs em tempo real (últimas 50 linhas)
docker-compose logs -f --tail=50 app

# Logs só de erros
docker-compose logs app | grep -i error

# Ver sistema de arquivos
docker-compose exec app df -h

# Ver espaço em disco do servidor
df -h /opt/multimax
```

### **Inspeção de Containers**

```bash
# Entrar no container (shell)
docker-compose exec app sh

# Sair do container
exit

# Ver histórico de containers (incluindo parados)
docker ps -a

# Ver informações detalhadas de um container
docker inspect $(docker-compose ps -q app)

# Ver variáveis de ambiente do container
docker-compose exec app env | grep -i flask
```

### **Banco de Dados**

```bash
# Backup do banco (se usando PostgreSQL em container)
docker-compose exec db pg_dump -U postgres multimax > backup_$(date +%Y%m%d_%H%M%S).sql

# Ver tamanho do banco
docker-compose exec app du -sh /app/instance/

# Limpar cache da aplicação
docker-compose exec app rm -rf /app/__pycache__
```

### **Performance e Recursos**

```bash
# Verificar uso de CPU e memória em tempo real
docker stats --no-stream

# Ver espaço ocupado por imagens Docker
docker images --format "table {{.Repository}}\t{{.Size}}"

# Limpar recursos não utilizados (cuidado!)
docker system prune -a --volumes
```

### **Certificados SSL/TLS (se usable)**

```bash
# Verificar certificado
sudo ls -la /etc/letsencrypt/live/

# Renovar certificado Let's Encrypt
sudo certbot renew --quiet

# Testar renovação (sem executar)
sudo certbot renew --dry-run
```

---

## 🔄 Rollback (Voltar para versão anterior)

Se algo der errado:

```bash
# Voltar para commit anterior
cd /opt/multimax
git log --oneline -5
git reset --hard <commit_hash>

# Reconstruir e reiniciar
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

**Exemplo:**
```bash
git reset --hard HEAD~1  # Volta para 1 commit anterior
```

---

## ⚠️ Análise de Obsolescência dos Comandos

| Comando | Status | Motivo | Alternativa |
|---------|--------|--------|-------------|
| `git fetch origin` | ✅ Ativo | Necessário para sincronizar | Manter |
| `git reset --hard origin/nova-versao-deploy` | ✅ Ativo | Força atualização limpa | Manter |
| `docker-compose build --no-cache` | ✅ Ativo | Rebuild de imagens | Manter ou considerar `docker buildx` (futura) |
| `docker-compose down` | ✅ Ativo | Para containers | Manter |
| `docker-compose up -d` | ✅ Ativo | Inicia containers | Manter |
| `sudo systemctl daemon-reload` | ✅ Ativo | Recarrega unidades systemd | Manter (necessário se arquivo `.service` mudou) |
| `sudo systemctl enable deploy-agent` | ✅ Ativo | Autostart na reboot | Manter |
| `sudo systemctl start deploy-agent` | ✅ Ativo | Inicia serviço | Manter |

**Conclusão:** Nenhum comando está obsoleto. Todos são necessários e válidos.

---

## 📝 Script Automático Completo

Crie um arquivo `/opt/multimax/deploy.sh`:

```bash
#!/bin/bash

set -e  # Exit on error

echo "=========================================="
echo "🚀 Iniciando Deployment MultiMax v2.6.71"
echo "=========================================="

# Pré-requisitos
echo "📋 Verificando pré-requisitos..."
cd /opt/multimax

# Sincronizar
echo "📥 Sincronizando com GitHub..."
git fetch origin
git reset --hard origin/nova-versao-deploy

# Build Docker
echo "🐳 Rebuilding Docker images..."
docker-compose build --no-cache

# Restart serviços
echo "🔄 Reiniciando containers..."
docker-compose down
docker-compose up -d

# Systemd
echo "⚙️  Recarregando systemd..."
sudo systemctl daemon-reload
sudo systemctl enable deploy-agent
sudo systemctl start deploy-agent

# Verificações
echo "✅ Verificando status..."
docker-compose ps
sudo systemctl status deploy-agent

echo ""
echo "=========================================="
echo "✨ Deployment concluído com sucesso!"
echo "=========================================="
echo ""
echo "Verificações úteis:"
echo "  docker-compose logs -f app"
echo "  sudo systemctl status deploy-agent"
echo "  curl http://localhost:5000/health"
```

**Usar:**
```bash
chmod +x /opt/multimax/deploy.sh
sudo ./deploy.sh
```

---

## 🆘 Troubleshooting

### Containers não iniciam
```bash
docker-compose logs app | tail -50
docker-compose down && docker-compose up -d
```

### Erro de permissão
```bash
sudo chown -R $USER:$USER /opt/multimax
sudo chmod -R 755 /opt/multimax
```

### Porta já em uso
```bash
lsof -i :5000
kill -9 <PID>
```

### Espaço em disco cheio
```bash
docker system prune -a
df -h
```

---

## 📞 Checklist Final

- [ ] Git sincronizado com `nova-versao-deploy`
- [ ] Docker images rebuiladas
- [ ] Containers rodando corretamente
- [ ] Deploy Agent iniciado
- [ ] Health check respondendo (curl http://localhost:5000/health)
- [ ] Logs sem erros críticos
- [ ] Versão correta exibida na aplicação

---

**Última atualização:** 20 de janeiro de 2026  
**Versão do documento:** 1.0
