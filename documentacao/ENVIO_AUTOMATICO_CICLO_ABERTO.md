# Configuração do Envio Automático de PDF de Ciclos Abertos

## Visão Geral

O sistema pode enviar automaticamente o PDF de ciclos abertos via WhatsApp todo **sábado às 20h** (horário de Brasília).

## Componentes

### 1. Script Cron

**Arquivo:** `cron/envio_ciclo_aberto.py`

**Função:** 
- Verifica se é sábado
- Verifica se está na janela de execução (19h-20h)
- Gera o PDF do ciclo aberto
- Envia mensagem via WhatsApp
- Registra logs de execução

### 2. Endpoint Manual

**Rota:** `POST /ciclos/enviar_pdf_ciclo_aberto`

**Botão na Interface:** "Ciclo Aberto" (verde, com ícone do WhatsApp)

**Acesso:** Disponível para usuários com nível `operador`, `admin` ou `DEV`

## Configuração no Servidor (VPS)

### Opção 1: Crontab (Recomendado)

1. Editar crontab do usuário:
```bash
crontab -e
```

2. Adicionar a linha (ajustar caminhos conforme necessário):
```bash
# Enviar PDF de ciclos abertos todo sábado às 20h (horário de Brasília)
0 20 * * 6 cd /opt/multimax && /opt/multimax/.venv/bin/python3 cron/envio_ciclo_aberto.py >> /var/log/multimax/cron_ciclo_aberto.log 2>&1
```

3. Verificar crontab instalado:
```bash
crontab -l
```

### Opção 2: Systemd Timer

1. Criar arquivo de serviço `/etc/systemd/system/envio-ciclo-aberto.service`:
```ini
[Unit]
Description=Envio automático de PDF de ciclos abertos via WhatsApp
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/opt/multimax
ExecStart=/opt/multimax/.venv/bin/python3 /opt/multimax/cron/envio_ciclo_aberto.py
StandardOutput=append:/var/log/multimax/cron_ciclo_aberto.log
StandardError=append:/var/log/multimax/cron_ciclo_aberto.log
```

2. Criar arquivo de timer `/etc/systemd/system/envio-ciclo-aberto.timer`:
```ini
[Unit]
Description=Timer para envio de PDF de ciclos abertos (sábados 20h)

[Timer]
# Executar todo sábado às 20h (horário do servidor, ajustar se necessário)
OnCalendar=Sat *-*-* 20:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

3. Ativar e iniciar o timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable envio-ciclo-aberto.timer
sudo systemctl start envio-ciclo-aberto.timer
```

4. Verificar status:
```bash
sudo systemctl status envio-ciclo-aberto.timer
sudo systemctl list-timers --all | grep envio-ciclo
```

## Criar Diretório de Logs

```bash
sudo mkdir -p /var/log/multimax
sudo chown www-data:www-data /var/log/multimax
```

## Testar Manualmente

### Teste do Script Cron

```bash
cd /opt/multimax
/opt/multimax/.venv/bin/python3 cron/envio_ciclo_aberto.py
```

**Nota:** O script só executa aos sábados entre 19h-20h. Para testar fora desse horário, comente as validações de data/hora no código.

### Teste do Endpoint via Interface

1. Acessar: `http://www.multimax.tec.br/ciclos/`
2. Clicar no botão verde "Ciclo Aberto"
3. Confirmar o envio
4. Verificar mensagem de sucesso/erro

### Teste via cURL

```bash
curl -X POST http://www.multimax.tec.br/ciclos/enviar_pdf_ciclo_aberto \
  -H "Cookie: session=SEU_COOKIE_AQUI" \
  -H "Content-Type: application/json"
```

## Verificar Logs

### Logs do Cron

```bash
tail -f /var/log/multimax/cron_ciclo_aberto.log
```

### Logs do Sistema (SystemLog)

Acessar via interface web: Menu → Logs do Sistema

Filtrar por:
- **Origem:** `cron_ciclo_aberto` ou `ciclos`
- **Evento:** `envio_automatico_sucesso`, `envio_automatico_falha`, `envio_pdf_ciclo_aberto`

## Mensagem Enviada

```
📊 *Registro de Ciclos - Colaboradores*

Segue anexo do registro de ciclos de todos os colaboradores, por favor, 
confiram seus próprios dias trabalhados, horas extras e todas as informações 
antes da conclusão final de todos os ciclos.

[Essa mensagem é enviada por um sistema automatizado existente em www.multimax.tec.br]
```

## Troubleshooting

### Script não executa no horário esperado

1. Verificar timezone do servidor:
```bash
timedatectl
```

2. Ajustar timezone se necessário:
```bash
sudo timedatectl set-timezone America/Sao_Paulo
```

### Erro "Não há dados de ciclos abertos"

- Normal se não houver registros de horas no ciclo atual
- O envio é automaticamente cancelado

### Erro ao enviar mensagem WhatsApp

1. Verificar conectividade do serviço WhatsApp:
```bash
docker-compose exec whatsapp-service sh -c "curl http://localhost:3001/health"
```

2. Verificar logs do WhatsApp:
```bash
docker-compose logs --tail 50 whatsapp-service
```

3. Verificar token configurado:
```bash
docker-compose exec multimax printenv WHATSAPP_SERVICE_TOKEN
```

### Permissões

Garantir que o script tem permissão de execução:
```bash
chmod +x /opt/multimax/cron/envio_ciclo_aberto.py
```

## Desabilitar Envio Automático

### Crontab

Comentar a linha no crontab:
```bash
crontab -e
# Adicionar # no início da linha
```

### Systemd Timer

```bash
sudo systemctl stop envio-ciclo-aberto.timer
sudo systemctl disable envio-ciclo-aberto.timer
```

## Horários Alternativos

Para alterar o horário de envio:

### Crontab

Ajustar os valores na linha do crontab:
```
# Formato: minuto hora dia mês dia_da_semana
# Exemplo: segunda às 8h30
30 8 * * 1 cd /opt/multimax && ...
```

### Systemd

Alterar a linha `OnCalendar` no arquivo `.timer`:
```ini
# Exemplo: segunda às 8h30
OnCalendar=Mon *-*-* 08:30:00
```

## Integração com Docker

Se o MultiMax está em Docker, usar `docker-compose exec`:

```bash
0 20 * * 6 cd /opt/multimax && docker-compose exec -T multimax /app/.venv/bin/python3 /app/cron/envio_ciclo_aberto.py >> /var/log/multimax/cron_ciclo_aberto.log 2>&1
```
