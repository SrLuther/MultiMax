# Proteção do Endpoint de Serviço WhatsApp

Este guia descreve como restringir o endpoint de serviço `/dev/whatsapp/enviar` para chamadas apenas locais (localhost) e validar o fluxo com token de serviço.

## Requisitos

- Token de serviço configurado: `WHATSAPP_SERVICE_TOKEN` (em variável de ambiente ou arquivo `.env.txt` na raiz do app)
- Nginx com reverse proxy para o Flask em `127.0.0.1:5000`

## Restrição por IP (Nginx)

Para permitir apenas chamadas internas ao servidor, adicione um bloco específico ao Nginx. Exemplo (ajuste conforme seu arquivo de site):

```nginx
location = /dev/whatsapp/enviar {
    # Permite apenas localhost
    allow 127.0.0.1;
    allow ::1;
    deny all;

    proxy_pass http://127.0.0.1:5000/dev/whatsapp/enviar;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_request_buffering off;
}
```

Alternativamente, se já existir `location /dev/` genérico, insira um `location = /dev/whatsapp/enviar` acima dele para sobrepor apenas este endpoint.

Após editar:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Teste de Validação

No VPS, execute:

```bash
./scripts/diagnostico-whatsapp-service.sh "SEU_TOKEN" "mensagem de teste"
```

Saídas esperadas:

- Sem Authorization: HTTP 302 (redirect para login)
- Com Authorization Bearer + localhost: HTTP 200 e JSON `{"ok": true}`

## Observações de Segurança

- O token nunca deve ser exposto fora do servidor.
- O endpoint continua exigindo token válido no Flask; a restrição Nginx apenas reduz a superfície de ataque.
- Logs do serviço WhatsApp e do Nginx ajudam a diagnosticar eventuais respostas 502.
