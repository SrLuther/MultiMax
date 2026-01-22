# Scripts de Automação - MultiMax

Este diretório contém scripts auxiliares para automação de tarefas de infraestrutura e deployment do sistema MultiMax.

---

## 📋 Índice

- [setup-whatsapp-infra.sh](#setup-whatsapp-infrash)
- [Pré-requisitos Gerais](#pré-requisitos-gerais)
- [Troubleshooting](#troubleshooting)

---

## 🚀 setup-whatsapp-infra.sh

**Script de automação para configurar infraestrutura do WhatsApp Service no MultiMax.**

### 📖 Descrição

Este script automatiza completamente a instalação e configuração do serviço WhatsApp no servidor VPS, incluindo:

- ✅ Instalação do Node.js 18+ (se necessário)
- ✅ Instalação do Nginx (se necessário)
- ✅ Criação de usuário dedicado `multimax`
- ✅ Configuração de diretórios e permissões
- ✅ Cópia do código do WhatsApp Service
- ✅ Instalação de dependências npm
- ✅ Criação do serviço systemd
- ✅ Configuração do Nginx com proxy reverso
- ✅ Validação pós-instalação com testes
- ✅ Guia interativo de próximos passos

### 🔧 Pré-requisitos

- **Sistema Operacional:** Ubuntu 20.04+ ou Debian 11+
- **Privilégios:** Acesso root/sudo
- **Rede:** Conexão com a internet
- **DNS:** Domínio configurado apontando para o servidor
- **Código:** Clonar o repositório MultiMax no servidor

### 📦 Uso

1. **Clonar o repositório:**

```bash
cd /tmp
git clone https://github.com/SrLuther/MultiMax.git
cd MultiMax
```

2. **Dar permissão de execução ao script:**

```bash
chmod +x scripts/setup-whatsapp-infra.sh
```

3. **Executar como root:**

```bash
sudo ./scripts/setup-whatsapp-infra.sh
```

4. **Seguir as instruções na tela:**

O script exibirá um banner de boas-vindas e executará todas as etapas automaticamente. Ao final, você verá:

```
╔══════════════════════════════════════════════════════╗
║            INSTALAÇÃO CONCLUÍDA COM SUCESSO          ║
╚══════════════════════════════════════════════════════╝

PRÓXIMOS PASSOS:

1. AUTENTICAR WHATSAPP:
   Ver QR Code: sudo journalctl -u whatsapp-service -f
   Escanear com WhatsApp no celular

2. CRIAR GRUPO 'Notify'

3. CONFIGURAR SSL/HTTPS:
   sudo certbot --nginx -d www.multimax.tec.br

4. TESTAR ENDPOINT PÚBLICO

5. CONFIGURAR MULTIMAX (.env)
```

### ✅ Validação Automática

O script realiza testes automáticos ao final:

- ✓ Verificação de porta 3001 escutando
- ✓ Teste HTTP do endpoint `/notify` local
- ✓ Validação de status do serviço systemd

### 🔧 Configuração Manual (após script)

#### 1. Autenticação WhatsApp

```bash
# Ver QR Code nos logs
sudo journalctl -u whatsapp-service -f
```

Escanear QR Code com:
- WhatsApp > Configurações > Aparelhos conectados > Conectar dispositivo

#### 2. Criar Grupo "Notify"

No WhatsApp, criar grupo chamado **"Notify"** (exatamente esse nome, sensível a maiúsculas/minúsculas).

#### 3. Configurar SSL (OBRIGATÓRIO para produção)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d www.multimax.tec.br -d multimax.tec.br

# Editar configuração Nginx
sudo nano /etc/nginx/sites-available/multimax

# Descomentar linhas de certificado SSL:
# ssl_certificate /etc/letsencrypt/live/www.multimax.tec.br/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/www.multimax.tec.br/privkey.pem;
# include /etc/letsencrypt/options-ssl-nginx.conf;
# ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

# Remover linhas de certificado temporário:
# ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
# ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

# Recarregar Nginx
sudo systemctl reload nginx
```

#### 4. Testar Endpoint Público

```bash
curl -X POST https://www.multimax.tec.br/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Teste automático de infraestrutura"}'
```

**Resposta esperada:**
```json
{"success": true}
```

#### 5. Configurar MultiMax

No arquivo `.env` do container MultiMax:

```env
WHATSAPP_NOTIFY_URL=https://www.multimax.tec.br/notify
```

Reiniciar container:

```bash
docker-compose restart multimax
```

### 📂 Estrutura Criada

Após execução bem-sucedida, a seguinte estrutura estará configurada:

```
/opt/multimax/whatsapp-service/
├── index.js                      # Código principal do serviço
├── package.json                  # Dependências npm
├── node_modules/                 # Bibliotecas instaladas
├── auth/                         # Sessão WhatsApp (criada após autenticação)
│   ├── creds.json
│   └── ...
└── README.md                     # Documentação do serviço

/etc/systemd/system/
└── whatsapp-service.service      # Serviço systemd

/etc/nginx/sites-available/
└── multimax                      # Configuração Nginx com proxy reverso

/var/log/nginx/
├── multimax_access.log
└── multimax_error.log

/var/log/
└── journal/                      # Logs do serviço (journalctl)
```

### 🛠️ Comandos Úteis

```bash
# Ver status do serviço
sudo systemctl status whatsapp-service

# Ver logs em tempo real
sudo journalctl -u whatsapp-service -f

# Reiniciar serviço
sudo systemctl restart whatsapp-service

# Parar serviço
sudo systemctl stop whatsapp-service

# Verificar configuração Nginx
sudo nginx -t

# Recarregar Nginx (sem downtime)
sudo systemctl reload nginx

# Testar endpoint local
curl -X POST http://localhost:3001/notify \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Teste local"}'
```

### 🐛 Troubleshooting

#### Problema: Porta 3001 não está escutando

**Solução:**
```bash
# Ver logs
sudo journalctl -u whatsapp-service -n 50

# Verificar se há outro processo usando a porta
sudo netstat -tuln | grep 3001

# Reiniciar serviço
sudo systemctl restart whatsapp-service
```

#### Problema: Nginx retorna 502 Bad Gateway

**Solução:**
```bash
# Verificar se o serviço está rodando
sudo systemctl status whatsapp-service

# Verificar conectividade local
curl http://localhost:3001/notify -v

# Ver logs do Nginx
sudo tail -f /var/log/nginx/multimax_error.log
```

#### Problema: QR Code não aparece nos logs

**Solução:**
```bash
# Remover sessão antiga
sudo rm -rf /opt/multimax/whatsapp-service/auth/*

# Reiniciar serviço
sudo systemctl restart whatsapp-service

# Ver logs (QR deve aparecer em ~5 segundos)
sudo journalctl -u whatsapp-service -f
```

#### Problema: Certificado SSL expirou

**Solução:**
```bash
# Renovar certificado
sudo certbot renew

# Recarregar Nginx
sudo systemctl reload nginx
```

### 📚 Documentação Completa

Para detalhes técnicos sobre a arquitetura, fluxos de comunicação e configurações avançadas, consulte:

- **[docs/infra-whatsapp.md](../docs/infra-whatsapp.md)** - Documentação completa de infraestrutura

### 🔒 Segurança

O script implementa as seguintes práticas de segurança:

- ✅ Usuário dedicado sem privilégios de root (`multimax`)
- ✅ Diretório de autenticação com permissões 700
- ✅ Limites de recursos (memoria, file descriptors)
- ✅ Proteção de sistema de arquivos (`ProtectSystem=strict`)
- ✅ Diretório temporário isolado (`PrivateTmp=true`)
- ✅ SSL/TLS obrigatório em produção
- ✅ Headers de segurança no Nginx

### 📝 Notas

- **Certificado Temporário:** O script usa um certificado autoassinado até você configurar o Certbot
- **Grupo Notify:** O nome do grupo deve ser **exatamente** "Notify" (case-sensitive)
- **Node.js 18+:** Versão mínima para compatibilidade com Baileys
- **Backup:** Sempre faça backup de `/opt/multimax/whatsapp-service/auth/` para preservar sessão
- **Logs:** São rotacionados automaticamente pelo journald (limite de ~100MB)

---

## 🔧 Pré-requisitos Gerais

Scripts neste diretório podem requerer:

- **Sistema:** Ubuntu/Debian (testado em 20.04+)
- **Privilégios:** Acesso root/sudo
- **Rede:** Internet ativa
- **Git:** Para clonar repositório

---

## 🐛 Troubleshooting

### Permissão Negada

```bash
chmod +x scripts/*.sh
```

### Erro "Command not found"

Executar com caminho completo:
```bash
sudo ./scripts/setup-whatsapp-infra.sh
```

### Script não funciona no Windows

Scripts `.sh` são para Linux/Unix. No Windows:
- Use WSL2 (Windows Subsystem for Linux)
- Ou execute diretamente no servidor VPS via SSH

---

## 📞 Suporte

Para problemas ou dúvidas:

1. Verificar documentação em [`docs/`](../docs/)
2. Consultar logs do sistema
3. Abrir issue no GitHub

---

**Última atualização:** 2026-01-22  
**Versão:** 3.0.7
