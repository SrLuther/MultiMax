# Guia de Teste do WhatsApp Gateway na VPS

## 🎯 Objetivo
Testar a correção do erro `Failed to establish a new connection: [Errno 111] Connection refused` na VPS após a implementação da detecção de ambiente Docker que desabilita fallbacks locais.

## 📋 Pré-requisitos
- Acesso SSH via alias configurado: `ssh multimax` (usa chave `id_ed25519_nopass`, sem senha)
- Código atualizado no GitHub

---

## 🚀 Método 1: Script Automatizado (Recomendado)

### 1. Conectar ao servidor via SSH
```bash
ssh multimax
```

### 2. Executar o script de teste
```bash
cd /opt/multimax
bash scripts/test-whatsapp-vps.sh
```

O script irá:
- ✅ Atualizar o código do repositório
- ✅ Reconstruir o container multimax
- ✅ Reiniciar os serviços
- ✅ Verificar conectividade entre containers
- ✅ Testar endpoint /health do whatsapp-service
- ✅ Enviar mensagem de teste

---

## 🔧 Método 2: Comandos Manuais

### 1. Atualizar código
```bash
cd /opt/multimax
git fetch origin
git pull origin nova-versao-deploy
```

### 2. Verificar última versão do código
```bash
git log --oneline -1
# Deve mostrar: 4aa593d fix(whatsapp): disable localhost fallbacks in Docker environment
```

### 3. Reconstruir container com nova versão
```bash
docker-compose build multimax
```

### 4. Reiniciar serviços
```bash
docker-compose up -d
```

### 5. Verificar status dos containers
```bash
docker-compose ps
```
Esperado: ambos `multimax` e `whatsapp-service` devem estar `Up`

### 6. Verificar logs do whatsapp-service
```bash
docker-compose logs --tail 30 whatsapp-service
```
Procure por:
- `✓ Conectado com sucesso ao WhatsApp`
- `Servidor HTTP rodando na porta 3001`
- `Grupo Notify identificado`

### 7. Testar conectividade de rede
```bash
docker-compose exec multimax getent hosts whatsapp-service
```
Esperado: uma linha resolvendo o hostname para um IP da rede docker (`172.x.x.x`)

### 8. Verificar variável de ambiente
```bash
docker exec multimax printenv WHATSAPP_NOTIFY_URL
```
Esperado: `http://whatsapp-service:3001/notify`

### 9. Verificar detecção do ambiente Docker
```bash
docker exec multimax test -f /.dockerenv && echo "Docker detectado (fallbacks desabilitados)" || echo "Não é Docker"
```
Esperado: `Docker detectado (fallbacks desabilitados)`

### 10. Testar endpoint /health internamente
```bash
docker-compose exec whatsapp-service sh -c "apk add --no-cache curl >/dev/null && curl -s http://localhost:3001/health"
```
Esperado: `{"status":"ok","service":"whatsapp-service"}`

### 11. Enviar mensagem de teste via endpoint Flask
```bash
# Obter o token
TOKEN=$(docker-compose exec multimax printenv WHATSAPP_SERVICE_TOKEN)

# Enviar mensagem de teste (instala curl se necessário)
docker-compose exec multimax sh -lc "apt-get update >/dev/null && apt-get install -y curl >/dev/null && curl -s -X POST \\
  -H 'Authorization: Bearer $TOKEN' \\
  -H 'Content-Type: application/json' \\
  -d '{\"numero\":\"5511999999999\",\"mensagem\":\"[TESTE VPS] Gateway funcionando!\"}' \\
  http://localhost:5000/dev/whatsapp/enviar"
```

**Respostas esperadas:**

✅ **Sucesso:**
```json
{"ok":true,"error":null}
```

❌ **Falha de conectividade (problema não resolvido):**
```json
{"ok":false,"error":"Falha ao contatar serviço WhatsApp: HTTPConnectionPool(host='whatsapp-service', port=3001): Max retries exceeded..."}
```

❌ **Token inválido:**
```json
{"ok":false,"error":"token inválido"}
```

---

## 🔍 Diagnóstico de Problemas

### Se o teste falhar com erro de conexão:

#### 1. Verificar se whatsapp-service está rodando
```bash
docker-compose ps whatsapp-service
```

#### 2. Verificar logs detalhados
```bash
docker-compose logs --tail 50 whatsapp-service
docker-compose logs --tail 50 multimax | grep -i whatsapp
```

#### 3. Verificar conectividade DNS
```bash
docker-compose exec multimax nslookup whatsapp-service
docker-compose exec multimax getent hosts whatsapp-service
```

#### 4. Verificar rede Docker
```bash
docker network ls
docker network inspect multimax-dev_default
```

#### 5. Verificar se o serviço está escutando na porta 3001
```bash
docker-compose exec whatsapp-service netstat -lnt | grep 3001
```

#### 6. Testar conexão direta
```bash
docker-compose exec multimax nc -zv whatsapp-service 3001
```

---

## 📊 Resultados Esperados

### ✅ Cenário de Sucesso

1. **Ambiente Docker detectado:** ✅
2. **whatsapp-service acessível:** ✅
3. **Fallbacks locais desabilitados:** ✅
4. **Mensagem enviada com sucesso:** ✅
5. **Logs sem erros de conexão:** ✅

### ❌ Cenário de Falha (problema persiste)

Se ainda ocorrer erro de conexão, verificar:
- whatsapp-service não está iniciando corretamente
- Problema na rede Docker
- Porta 3001 não está acessível
- Grupo "Notify" não foi configurado no WhatsApp

---

## 📝 Próximos Passos

### Se o teste passar:
1. ✅ Marcar tarefa como concluída
2. ✅ Monitorar logs em produção nas próximas horas
3. ✅ Validar envio de notificações reais

### Se o teste falhar:
1. 🔍 Coletar logs completos: `docker-compose logs > debug-whatsapp.log`
2. 🔍 Verificar se whatsapp-service precisa ser reconectado ao WhatsApp
3. 🔍 Validar configuração do docker-compose.yml
4. 🔍 Verificar se há algum firewall/iptables bloqueando

---

## 📞 Suporte

Em caso de problemas, fornecer:
- Saída completa do script de teste
- Logs dos containers: `docker-compose logs`
- Resultado dos comandos de diagnóstico
- Screenshot do erro (se aplicável)
