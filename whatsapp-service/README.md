# WhatsApp Service (Baileys)

Serviço Node.js em modo daemon para integração contínua com WhatsApp Web via Baileys. Mantém conexão ativa, reconecta automaticamente e expõe endpoint HTTP para envio de mensagens.

**Integração exclusiva com WhatsApp** — Sem Telegram ou outros mensageiros.

## Requisitos
- Node.js 18+ (com suporte a `crypto.webcrypto`)
- npm
- Grupo WhatsApp chamado **"Notify"** (case-insensitive)

## Instalação
```bash
cd whatsapp-service
npm install
```

## Uso
```bash
npm start
# ou
node index.js
```

**O serviço permanecerá ativo indefinidamente** após a conexão.

Fluxo:
1) O terminal exibirá um QR Code (modo texto). Escaneie com o WhatsApp no celular: *Configurações > Aparelhos conectados > Conectar dispositivo*.
2) Após a conexão, o serviço listará todos os grupos com:
   ```
   <nome do grupo> -> <group_id>
   ```
3) O serviço **permanece ativo** aguardando eventos e rotinas futuras.
4) Reconexão automática em caso de queda (exceto logout).
5) **Servidor HTTP na porta 3001** pronto para receber requisições.

Para **parar o serviço**: `Ctrl+C` (SIGINT) ou `kill <pid>` (SIGTERM).

## Endpoint HTTP

### POST `/notify`
Envia mensagem imediatamente para o grupo **Notify**.

**Request:**
```json
{
  "mensagem": "Texto da mensagem"
}
```

**Response 200:**
```json
{
  "sucesso": true,
  "mensagem": "Enviado para grupo Notify"
}
```

**Response 500:**
```json
{
  "erro": "Descrição do erro"
}
```

**Exemplo com curl:**
```bash
curl -X POST http://localhost:3001/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Olá do MultiMax!"}'
```

## Persistência de sessão
- A autenticação fica em `whatsapp-service/auth/` (ignorada pelo git).
- Se precisar reconectar do zero (ex.: sessão expirada), delete a pasta `auth/` e rode novamente.
- Reconexão automática em quedas temporárias (timeout em 5 segundos).

## Segurança
- Nenhum ID de grupo é armazenado; apenas impresso no console.
- Sem credenciais hardcoded.
- Pasta `auth/` está no `.gitignore` para evitar commit acidental.
- Crypto injetado globalmente para compatibilidade com Node 18.

## Resolução de problemas

### "ReferenceError: crypto is not defined"
Já está resolvido no código. O `crypto.webcrypto` é injetado automaticamente no topo do `index.js`.

### Sessão expirada
Delete a pasta `whatsapp-service/auth/` e rode novamente:
```bash
rm -rf auth/
npm start
```

## Próximos passos (fora do escopo atual)
- Implementar autenticação no endpoint /notify
- Adicionar tarefas periódicas/automatizadas (estrutura já preparada em `setupAutomatedTasks()`).
- Suporte a múltiplos grupos via parâmetro

## Modo Daemon
O serviço roda continuamente em modo daemon:
- ✓ Reconexão automática
- ✓ Endpoint HTTP POST /notify (porta 3001)
- ✓ Envio imediato para grupo "Notify"
- ✓ Logs estruturados (pino)
- ✓ Ignora erros de histórico do WhatsApp
- ✓ Estrutura para rotinas periódicas
- ✓ Shutdown gracioso (SIGINT/SIGTERM)
