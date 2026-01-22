# WhatsApp Service (Baileys)

Serviço Node.js local para autenticar via WhatsApp Web, listar todos os grupos do número conectado e exibir `GROUP ID` (formato `@g.us`). Nenhum envio é feito nesta fase.

## Requisitos
- Node.js 18+
- npm

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

Fluxo:
1) O terminal exibirá um QR Code (modo texto). Escaneie com o WhatsApp no celular: *Configurações > Aparelhos conectados > Conectar dispositivo*.
2) Após a conexão, o serviço listará todos os grupos com:
   ```
   <nome do grupo> -> <group_id>
   ```
3) Copie o `group_id` (termina com `@g.us`). O processo encerra automaticamente depois de listar.

## Persistência de sessão
- A autenticação fica em `whatsapp-service/auth/` (ignorada pelo git).
- Se precisar reconectar do zero (ex.: sessão expirada), delete a pasta `auth/` e rode novamente.

## Segurança
- Nenhum ID de grupo é armazenado; apenas impresso no console.
- Sem credenciais hardcoded.
- Pasta `auth/` está no `.gitignore` para evitar commit acidental.

## Próximos passos (fora do escopo atual)
- Expor endpoint HTTP local para o Multimax consumir.
- Implementar envio para grupos usando os IDs capturados.
