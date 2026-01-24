# Script de Deploy Automático para VPS MultiMax

## 📋 Visão Geral

Script bash aprimorado que executa o deploy da aplicação MultiMax na VPS com:
- ✅ Tratamento robusto de erros
- ✅ Verificação em cada etapa
- ✅ Feedback colorido e informativo
- ✅ Limpeza completa de recursos antigos
- ✅ Verificação de sucesso final

## 🚀 Como Usar

### Opção 1: Executar diretamente (one-liner)
```bash
cd /opt/multimax && bash <(curl -s https://raw.githubusercontent.com/SrLuther/MultiMax/nova-versao-deploy/deploy-vps-improved.sh)
```

### Opção 2: Copiar e executar no servidor
```bash
# Copiar arquivo do repositório
scp deploy-vps-improved.sh multimax@157.230.170.248:/opt/multimax/

# Executar no servidor
ssh multimax@157.230.170.248 "cd /opt/multimax && chmod +x deploy-vps-improved.sh && bash deploy-vps-improved.sh"
```

### Opção 3: Executar manualmente na VPS
```bash
ssh multimax@157.230.170.248
cd /opt/multimax
curl -o deploy.sh https://raw.githubusercontent.com/SrLuther/MultiMax/nova-versao-deploy/deploy-vps-improved.sh
bash deploy.sh
```

## 📊 O que o Script Faz

| Etapa | Ação | Descrição |
|-------|------|-----------|
| 1️⃣ | Git Fetch | Busca atualizações do repositório remoto |
| 2️⃣ | Git Reset | Reseta para a versão mais recente da branch `nova-versao-deploy` |
| 3️⃣ | Docker Down | Para todos os containers gerenciados pelo docker-compose |
| 4️⃣ | Sleep | Aguarda 3 segundos para liberar recursos |
| 5️⃣ | Remove Containers | Remove containers antigos da aplicação |
| 6️⃣ | Prune Networks | Limpa redes Docker não utilizadas |
| 7️⃣ | Prune Volumes | Limpa volumes não utilizados |
| 8️⃣ | Prune Images | Limpa imagens dangling |
| 9️⃣ | Build Image | Reconstrói a imagem Docker sem cache |
| 🔟 | Up Compose | Inicia o container em background |
| 1️⃣1️⃣ | Sleep 15s | Aguarda inicialização da aplicação |
| 1️⃣2️⃣ | Verificações | Verifica se container está rodando e mostra logs |

## ⚡ Melhorias em Relação ao Script Original

### ✅ Tratamento de Erros
```bash
# Original: Continua mesmo com erros
docker-compose down --remove-orphans && \
docker-compose build --no-cache  # Executa mesmo se down falhar

# Melhorado: Para na primeira falha com set -e
set -e
docker-compose down --remove-orphans || warning "..."
```

### ✅ Delay entre Down e Remove
```bash
# Problema: Race condition entre remoção
docker-compose down --remove-orphans && \
docker ps -a | grep multimax | awk '{print $1}' | xargs -r docker rm -f

# Solução: Aguarda 3 segundos
docker-compose down --remove-orphans
sleep 3  # Libera recursos
docker ps -a | grep multimax | awk '{print $1}' | xargs -r docker rm -f
```

### ✅ Limpeza de Imagens
```bash
# Original: Não remove imagens antigas
docker volume prune -f

# Melhorado: Remove imagens dangling
docker image prune -f
```

### ✅ Verificação Final
```bash
# Original: Não verifica se subiu com sucesso
docker-compose up -d

# Melhorado: Aguarda 15s e verifica status
docker-compose up -d
sleep 15
docker ps | grep -q multimax || error_exit "Container não está rodando!"
```

### ✅ Logging Estruturado
```bash
# Original: Sem informações claras
echo "Atualizando..."

# Melhorado: Feedback colorido e organizado
echo -e "${GREEN}✅ Git fetch completado${NC}"
warning "⚠️  docker-compose down encontrou problemas, continuando..."
error_exit "❌ ERRO: Falha ao construir imagem Docker"
```

## 📝 Variáveis Customizáveis

Se precisar customizar, edite estas variáveis no script:

```bash
# Tempo de espera após docker-compose down (em segundos)
sleep 3

# Tempo de espera para inicialização (em segundos)
sleep 15

# Branch a fazer deploy
git reset --hard origin/nova-versao-deploy
```

## 🔧 Troubleshooting

### Se o container não subir:
```bash
# Ver logs completos
docker logs multimax

# Verificar status
docker ps -a | grep multimax

# Reiniciar manualmente
cd /opt/multimax
docker-compose down
docker-compose up -d
```

### Se houver erro de porta:
```bash
# Verificar qual processo está usando porta 5000
sudo lsof -i :5000
sudo netstat -tuln | grep 5000

# Matar processo se necessário
sudo kill -9 <PID>
```

### Se houver erro de permissão:
```bash
# Garantir que usuário multimax tem acesso
sudo chown -R multimax:multimax /opt/multimax
sudo chmod -R 755 /opt/multimax
```

## 📅 Agendamento (Cron)

Para executar deploy automaticamente diariamente:

```bash
# Editar crontab
crontab -e

# Adicionar linha para executar às 2AM diariamente
0 2 * * * cd /opt/multimax && bash deploy-vps-improved.sh >> /var/log/multimax-deploy.log 2>&1
```

## 🔐 Segurança

⚠️ **Aviso:** Este script usa `git reset --hard`, que descarta mudanças locais. Certifique-se que:
- O repositório remoto está sincronizado
- Não há commits locais que queira manter
- Backups estão atualizados

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs: `docker logs multimax`
2. Verifique espaço em disco: `df -h`
3. Verifique espaço Docker: `docker system df`
4. Abra uma issue no repositório com os logs
