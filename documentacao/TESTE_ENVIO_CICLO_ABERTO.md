# Guia Rápido de Teste - Envio Automático de Ciclo Aberto

## Pré-requisitos

✅ WhatsApp service conectado e funcionando  
✅ Colaboradores com registros de horas no ciclo atual  
✅ Acesso à VPS via SSH (alias `multimax`)

## 1. Teste Local (Desenvolvimento)

### Teste do Endpoint via Interface

1. Iniciar aplicação local:
```bash
python app.py
```

2. Acessar: http://127.0.0.1:5000/ciclos/

3. Localizar botão verde "Ciclo Aberto" (ao lado de "Registrar Pagamento")

4. Clicar no botão e confirmar

5. **Resultado esperado:**
   - Alert de sucesso: "✅ Mensagem enviada com sucesso via WhatsApp!"
   - Mensagem aparece no grupo WhatsApp Notify
   - Log criado na tabela SystemLog

### Teste do Script Cron (Sem validação de horário)

1. Comentar temporariamente as validações de dia/hora no script:

```python
# No arquivo cron/envio_ciclo_aberto.py, comentar:
# if dia_semana != 5:
#     ...
#     return
# if not (19 <= hora <= 20):
#     ...
#     return
```

2. Executar script:
```bash
python cron/envio_ciclo_aberto.py
```

3. **Resultado esperado:**
```
Gerando PDF de ciclo aberto...
PDF gerado com sucesso (Ciclo X, MÊS)
Enviando mensagem via WhatsApp...
✅ Mensagem enviada com sucesso via WhatsApp
```

4. Reverter comentários após o teste

## 2. Teste na VPS

### Conectar via SSH

```bash
ssh multimax
cd /opt/multimax
```

### Teste do Botão via Interface Web

1. Acessar: https://www.multimax.tec.br/ciclos/

2. Login com usuário admin/operador

3. Clicar no botão "Ciclo Aberto"

4. Verificar mensagem no WhatsApp

### Teste do Endpoint via cURL

```bash
# Obter cookie de sessão (logar via browser e copiar cookie)
curl -X POST https://www.multimax.tec.br/ciclos/enviar_pdf_ciclo_aberto \
  -H "Cookie: session=SEU_COOKIE_AQUI" \
  -H "Content-Type: application/json"
```

**Resposta esperada:**
```json
{"ok": true, "message": "Mensagem enviada com sucesso via WhatsApp"}
```

### Teste do Script Cron (Simulação)

**Opção A: Executar via Docker**

```bash
docker-compose exec -T multimax /app/.venv/bin/python3 /app/cron/envio_ciclo_aberto.py
```

**Opção B: Executar diretamente (se não usar Docker)**

```bash
/opt/multimax/.venv/bin/python3 /opt/multimax/cron/envio_ciclo_aberto.py
```

**Nota:** O script só executa aos sábados entre 19h-20h. Para testar, edite temporariamente o código removendo as validações de data/hora.

## 3. Verificação de Logs

### Logs do Sistema (Interface Web)

1. Acessar: Menu → Logs do Sistema

2. Filtrar por:
   - **Origem:** `ciclos` ou `cron_ciclo_aberto`
   - **Evento:** `envio_pdf_ciclo_aberto`, `envio_automatico_sucesso`

3. Verificar detalhes do último envio

### Logs do Cron (Servidor)

```bash
# Se configurou log file
tail -f /var/log/multimax/cron_ciclo_aberto.log

# Logs do sistema
journalctl -u envio-ciclo-aberto.service -f
```

### Logs do WhatsApp Service

```bash
docker-compose logs --tail 50 whatsapp-service
```

## 4. Checklist de Validação

### ✅ Funcionalidade Básica

- [ ] Botão "Ciclo Aberto" aparece na interface
- [ ] Botão está verde com ícone do WhatsApp
- [ ] Botão desabilita durante o envio ("Enviando...")
- [ ] Mensagem de sucesso/erro aparece após o envio
- [ ] Mensagem chega no grupo WhatsApp Notify

### ✅ Conteúdo da Mensagem

- [ ] Título: "📊 *Registro de Ciclos - Colaboradores*"
- [ ] Texto completo presente
- [ ] Rodapé com link do site
- [ ] Formatação em Markdown preservada

### ✅ Geração do PDF

- [ ] PDF é gerado sem erros
- [ ] PDF contém dados de todos os colaboradores
- [ ] PDF inclui totalizadores
- [ ] Logo da empresa aparece no PDF

### ✅ Logs e Auditoria

- [ ] Registro criado no SystemLog
- [ ] Origem correta (`ciclos` ou `cron_ciclo_aberto`)
- [ ] Detalhes incluem ciclo_id e mês
- [ ] Usuário registrado corretamente

### ✅ Agendamento (Cron)

- [ ] Crontab configurado corretamente
- [ ] Script executa apenas aos sábados
- [ ] Script executa apenas entre 19h-20h
- [ ] Logs sendo gravados em arquivo

## 5. Casos de Teste

### Caso 1: Ciclo com dados

**Cenário:** Existem registros de horas no ciclo atual

**Passos:**
1. Clicar no botão "Ciclo Aberto"
2. Confirmar envio

**Resultado esperado:**
- Mensagem enviada com sucesso
- PDF gerado com todos os colaboradores

### Caso 2: Ciclo sem dados

**Cenário:** Não existem registros de horas no ciclo atual

**Passos:**
1. Remover todos os registros do ciclo atual (opcional)
2. Clicar no botão "Ciclo Aberto"
3. Confirmar envio

**Resultado esperado:**
- Erro: "Não há dados de ciclos abertos para enviar"

### Caso 3: Usuário sem permissão

**Cenário:** Usuário com nível diferente de admin/operador/DEV

**Passos:**
1. Fazer login com usuário comum
2. Tentar acessar endpoint diretamente

**Resultado esperado:**
- Erro 403: "Acesso negado"
- Botão não aparece na interface

### Caso 4: WhatsApp desconectado

**Cenário:** Serviço WhatsApp está offline

**Passos:**
1. Parar serviço: `docker-compose stop whatsapp-service`
2. Clicar no botão "Ciclo Aberto"
3. Confirmar envio

**Resultado esperado:**
- Erro: "Erro ao enviar mensagem: Falha ao contatar serviço WhatsApp"

### Caso 5: Execução automática (Sábado 20h)

**Cenário:** Script cron é executado automaticamente

**Passos:**
1. Aguardar sábado às 20h (ou simular)
2. Verificar logs do cron
3. Verificar mensagem no WhatsApp

**Resultado esperado:**
- Script executa sem erros
- Mensagem enviada automaticamente
- Log registrado com origem `cron_ciclo_aberto`

## 6. Comandos Úteis

### Verificar se o serviço WhatsApp está funcionando

```bash
docker-compose exec whatsapp-service sh -c "curl http://localhost:3001/health"
```

### Verificar próximas execuções do cron

```bash
# Crontab
# (não há comando direto, verificar manualmente)

# Systemd timer
systemctl list-timers --all | grep envio-ciclo
```

### Simular horário de execução

```bash
# Executar o script ignorando validações
# (requer edição temporária do código)
```

### Limpar logs

```bash
> /var/log/multimax/cron_ciclo_aberto.log
```

## 7. Problemas Conhecidos

### ⚠️ Anexo PDF não enviado

**Status:** Funcionalidade não implementada

**Motivo:** A função `send_whatsapp_message()` atual não suporta anexos

**Solução futura:** 
- Expandir `send_whatsapp_message()` para aceitar parâmetro `attachment`
- Modificar serviço WhatsApp para suportar envio de arquivos
- Integrar com Baileys para envio de documentos

**Workaround atual:** Apenas a mensagem de texto é enviada

## 8. Próximos Passos

1. **Testar em desenvolvimento local** (itens 1-3 do checklist)
2. **Fazer deploy na VPS** (`git push`, pull no servidor)
3. **Testar na VPS** (item 4 do checklist)
4. **Configurar cron** (seguir documentação em `ENVIO_AUTOMATICO_CICLO_ABERTO.md`)
5. **Aguardar próximo sábado** ou simular execução
6. **Monitorar logs** na primeira semana

## 9. Rollback

Se necessário reverter:

1. **Desabilitar cron:**
```bash
crontab -e
# Comentar linha do envio_ciclo_aberto.py
```

2. **Reverter código:**
```bash
git revert HEAD
git push origin nova-versao-deploy
```

3. **Reload na VPS:**
```bash
git pull
docker-compose restart multimax
```
