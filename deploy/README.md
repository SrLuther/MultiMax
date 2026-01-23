# MultiMax Deploy - README

## 📋 Visão Geral

Este diretório contém **toda a lógica de deploy, instalação e gerenciamento** do MultiMax para ambiente de produção (Ubuntu 24.04 LTS).

### Estrutura

```
deploy/
├── setup.sh                  # 🚀 Script principal (instala tudo)
├── scripts/
│   ├── app-manager.sh        # Gerencia ciclo de vida da aplicação
│   └── db-manager.sh         # Gerencia banco de dados
├── config/
│   └── .env.example          # Template de configuração
├── systemd/
│   └── multimax.service      # Unit file para systemd
└── docs/
    ├── DEPLOYMENT.md         # Guia completo de deploy
    ├── NGINX.md              # Configuração Nginx
    ├── DATABASE.md           # Configuração de banco
    └── SYSTEMD.md            # Detalhes do systemd
```

---

## 🚀 Instalação Rápida

### Opção 1: Automatizada (recomendado)

```bash
# 1. Clonar repo
git clone https://github.com/seu-usuario/MultiMax.git
cd MultiMax

# 2. Executar setup (como root ou via sudo)
sudo ./deploy/setup.sh

# 3. Configurar variáveis de ambiente
sudo nano /opt/multimax/.env

# 4. Iniciar aplicação
sudo systemctl start multimax
sudo systemctl status multimax
```

### Opção 2: Passo a Passo

```bash
# Instalar dependências do SO manualmente
sudo ./deploy/setup.sh --skip-os-deps

# Criar e configurar .env
cp deploy/config/.env.example /opt/multimax/.env
sudo nano /opt/multimax/.env

# Inicializar banco de dados
sudo -u multimax ./deploy/scripts/db-manager.sh init

# Iniciar aplicação
sudo -u multimax ./deploy/scripts/app-manager.sh start
```

---

## 📚 Scripts Principais

### `setup.sh` - Instalação Completa

Automatiza toda instalação de produção.

**O que faz:**
- ✅ Verifica pré-requisitos (Ubuntu, root)
- ✅ Instala dependências do SO (apt-get)
- ✅ Cria usuário não-root `multimax`
- ✅ Estrutura diretórios (`/opt/multimax`, `/var/lib/multimax`)
- ✅ Configura Python venv
- ✅ Instala dependências Python (requirements.txt)
- ✅ Cria arquivo `.env` seguro
- ✅ Inicializa banco de dados
- ✅ Instala serviço systemd
- ✅ Configura Nginx (template)

**Uso:**
```bash
sudo ./deploy/setup.sh [opções]

# Opções:
--skip-os-deps              # Pula instalação de deps do SO
--skip-db                   # Pula inicialização de banco
--user=multimax             # Customizar usuário
--home=/opt/multimax        # Customizar home directory
--data-dir=/var/lib/multimax # Customizar data directory
```

**Exemplos:**
```bash
# Instalação padrão (Ubuntu 24.04)
sudo ./deploy/setup.sh

# Se dependências já instaladas
sudo ./deploy/setup.sh --skip-os-deps

# Usar usuário customizado
sudo ./deploy/setup.sh --user=app --home=/opt/app
```

---

### `scripts/app-manager.sh` - Gerenciador de Aplicação

Controla ciclo de vida da aplicação (start, stop, restart, logs).

**Uso:**
```bash
cd /opt/multimax/deploy/scripts

# Iniciar
sudo -u multimax ./app-manager.sh start

# Parar
sudo -u multimax ./app-manager.sh stop

# Reiniciar
sudo -u multimax ./app-manager.sh restart

# Status
./app-manager.sh status

# Logs (tempo real)
./app-manager.sh logs
```

**ou via systemd:**
```bash
sudo systemctl start multimax
sudo systemctl stop multimax
sudo systemctl restart multimax
sudo systemctl status multimax
sudo journalctl -u multimax -f
```

---

### `scripts/db-manager.sh` - Gerenciador de Banco

Controla banco de dados (init, backup, restore, status).

**Uso:**
```bash
cd /opt/multimax/deploy/scripts

# Inicializar (primeira vez)
sudo -u multimax ./db-manager.sh init

# Fazer backup
sudo -u multimax ./db-manager.sh backup

# Ver lista de backups
ls -lh /var/lib/multimax/backups/

# Restaurar
sudo -u multimax ./db-manager.sh restore /var/lib/multimax/backups/multimax_20260123_120000.sql.gz

# Status
./db-manager.sh status
```

---

## ⚙️ Configuração

### Arquivo `.env`

Copiar `deploy/config/.env.example` para `/opt/multimax/.env` e configurar:

```bash
# Obrigatório
SECRET_KEY=seu_chave_secreta_aqui
DATABASE_URL=postgresql://user:pass@host/db

# Recomendado
FLASK_ENV=production
MAINTENANCE_MODE=false

# Opcional
MULTIMAX_HOST=0.0.0.0
MULTIMAX_PORT=5000
LOG_LEVEL=INFO
```

**Segurança:**
- `chmod 600 /opt/multimax/.env` (só owner lê)
- **Nunca** commite `.env` no git
- Usar senhas fortes no banco de dados
- Gerar `SECRET_KEY` segura: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## 🔄 Operações Comuns

### Iniciar aplicação na primeira vez

```bash
# Executar setup (instala tudo)
sudo ./deploy/setup.sh

# Editar .env
sudo nano /opt/multimax/.env

# Iniciar
sudo systemctl start multimax

# Verificar status
sudo systemctl status multimax
```

### Parar e reiniciar

```bash
sudo systemctl stop multimax
sudo systemctl restart multimax
```

### Ver logs

```bash
# Logs do systemd
sudo journalctl -u multimax -f

# Últimas 50 linhas
sudo journalctl -u multimax -n 50

# Logs de arquivo
tail -f /var/lib/multimax/logs/multimax.log
```

### Fazer backup do banco

```bash
sudo -u multimax /opt/multimax/deploy/scripts/db-manager.sh backup
```

### Atualizar código

```bash
cd /opt/multimax

# Pull da branch main
sudo -u multimax git pull origin main

# Instalar novas dependências
source venv/bin/activate
pip install -r requirements.txt

# Restart
sudo systemctl restart multimax
```

### Ativar modo de manutenção

```bash
# Editar .env
sudo sed -i 's/MAINTENANCE_MODE=false/MAINTENANCE_MODE=true/' /opt/multimax/.env

# Restart
sudo systemctl restart multimax

# Para desativar
sudo sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' /opt/multimax/.env
sudo systemctl restart multimax
```

---

## 🛡️ Segurança

### Checklist de Produção

- [ ] Mudar `SECRET_KEY` em `.env`
- [ ] Usar senha forte para PostgreSQL
- [ ] Configurar SSL/TLS (Let's Encrypt)
- [ ] Configurar firewall (UFW)
- [ ] Desabilitar SSH direto para root
- [ ] Usar chaves SSH (não senha)
- [ ] Fazer backups regulares
- [ ] Monitorar logs
- [ ] Usar HTTPS em produção

### Permissões de Arquivo

```bash
# Config (contém credenciais)
sudo chmod 600 /opt/multimax/.env

# Código e venv
sudo chmod 755 /opt/multimax

# Data directory
sudo chmod 755 /var/lib/multimax
sudo chmod 700 /var/lib/multimax/backups
```

### Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## 🔧 Troubleshooting

### A aplicação não inicia

```bash
# 1. Checar logs
sudo journalctl -u multimax -n 50

# 2. Testar importação Python
sudo -u multimax /opt/multimax/venv/bin/python -c "from multimax import create_app; create_app()"

# 3. Verificar permissões
ls -la /opt/multimax/.env
ls -la /var/lib/multimax/

# 4. Testar banco de dados
sudo -u multimax psql postgresql://multimax:PASSWORD@localhost/multimax_db
```

### Nginx retorna 502 Bad Gateway

```bash
# 1. Verificar se app está rodando
sudo systemctl status multimax

# 2. Testar porta local
curl -I http://localhost:5000/

# 3. Ver erro do Nginx
sudo tail -20 /var/log/nginx/error.log
```

### Erro de permissão

```bash
# Corrigir proprietário
sudo chown -R multimax:multimax /opt/multimax
sudo chown -R multimax:multimax /var/lib/multimax

# Corrigir permissões
sudo chmod 755 /opt/multimax
sudo chmod 700 /opt/multimax/.env
sudo chmod 755 /var/lib/multimax
```

---

## 📖 Documentação Completa

Para mais detalhes, veja:

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Guia completo de instalação e operação
- **[NGINX.md](docs/NGINX.md)** - Configuração Nginx avançada
- **[DATABASE.md](docs/DATABASE.md)** - Configuração de banco de dados
- **[SYSTEMD.md](docs/SYSTEMD.md)** - Detalhes do systemd

---

## 📞 Suporte

Qualquer problema, veja os logs:

```bash
# Systemd journal
sudo journalctl -u multimax -f

# Arquivo de log
tail -f /var/lib/multimax/logs/multimax.log

# Nginx
sudo tail -f /var/log/nginx/error.log
```

---

**Deploy v3.0.17** | **MultiMax** | **Ubuntu 24.04 LTS**
