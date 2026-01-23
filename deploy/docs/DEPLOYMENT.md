# MultiMax - Guia de Deploy em Produção (Ubuntu 24.04 LTS)

## Visão Geral

Este guia descreve como instalar, configurar e gerenciar o MultiMax em um servidor Ubuntu 24.04 LTS com máxima automação, confiabilidade e segurança.

## Arquitetura de Deploy

```
┌─────────────────────────────────────────────┐
│  Cliente / Navegador                        │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  Nginx (Reverse Proxy)                      │
│  - SSL/TLS                                  │
│  - Load Balancing                           │
│  - Static Files                             │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  MultiMax (Flask Application)               │
│  - User: multimax (non-root)                │
│  - Port: 5000 (interno)                     │
│  - Home: /opt/multimax                      │
│  - venv: /opt/multimax/venv                 │
│  - Gerencido por: systemd                   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  PostgreSQL / SQLite                        │
│  Data: /var/lib/multimax                    │
│  Backups: /var/lib/multimax/backups         │
└─────────────────────────────────────────────┘
```

## Pré-Requisitos

### Hardware Mínimo
- CPU: 2 cores
- RAM: 2 GB (4 GB recomendado)
- Disco: 10 GB (expandível conforme necessário)
- Internet: conexão estável

### Software
- Ubuntu 24.04 LTS (ou 22.04, 20.04)
- Git
- Acesso root via sudo

### Domínio (para produção)
- Domínio registrado
- SSL/TLS (Let's Encrypt gratuito)

---

## Instalação Rápida

### 1. Clonar Repositório

```bash
cd /tmp
git clone https://github.com/seu-usuario/MultiMax.git
cd MultiMax
```

### 2. Executar Setup (como root ou via sudo)

```bash
sudo ./deploy/setup.sh
```

**Opções do setup:**
```bash
# Pular instalação de dependências do SO
sudo ./deploy/setup.sh --skip-os-deps

# Pular inicialização de banco de dados
sudo ./deploy/setup.sh --skip-db

# Usar usuário/home customizados
sudo ./deploy/setup.sh --user=myapp --home=/opt/myapp --data-dir=/data/myapp
```

### 3. Configurar Ambiente

```bash
sudo nano /opt/multimax/.env
```

Editar ao mínimo:
- `SECRET_KEY`: Gerar uma chave segura
- `DATABASE_URL`: URL do banco de dados
- `MULTIMAX_HOST`: 0.0.0.0 se atrás do Nginx

### 4. Iniciar Aplicação

```bash
# Via systemd
sudo systemctl start multimax
sudo systemctl status multimax

# Ou manualmente
cd /opt/multimax
sudo -u multimax ./deploy/scripts/app-manager.sh start
```

### 5. Configurar Nginx (opcional mas recomendado)

```bash
# Habilitar site
sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Recarregar
sudo systemctl reload nginx
```

### 6. Configurar SSL com Let's Encrypt (recomendado)

```bash
# Instalar Certbot
sudo apt-get install certbot python3-certbot-nginx

# Gerar certificado
sudo certbot --nginx -d seu-dominio.com

# Renovação automática (já ativado por padrão)
sudo systemctl enable certbot.timer
```

---

## Gerenciamento da Aplicação

### Iniciar/Parar/Reiniciar

#### Via systemd (recomendado)
```bash
sudo systemctl start multimax
sudo systemctl stop multimax
sudo systemctl restart multimax
sudo systemctl status multimax
```

#### Via script
```bash
cd /opt/multimax/deploy/scripts
sudo -u multimax ./app-manager.sh start
sudo -u multimax ./app-manager.sh stop
sudo -u multimax ./app-manager.sh status
sudo -u multimax ./app-manager.sh logs
```

### Ver Logs

```bash
# Systemd journal
sudo journalctl -u multimax -f

# Arquivo de log
tail -f /var/lib/multimax/logs/multimax.log

# Via script
sudo -u multimax /opt/multimax/deploy/scripts/app-manager.sh logs
```

### Fazer Backup do Banco

```bash
cd /opt/multimax/deploy/scripts
sudo -u multimax ./db-manager.sh backup
```

Backups armazenados em: `/var/lib/multimax/backups/`

### Restaurar Backup

```bash
sudo -u multimax ./db-manager.sh restore /var/lib/multimax/backups/multimax_20260123_120000.sql.gz
```

---

## Atualização do MultiMax

### Método 1: Git (recomendado)

```bash
cd /opt/multimax
sudo -u multimax git pull origin main

# Instalar novas dependências
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar
sudo systemctl restart multimax
```

### Método 2: Build Manual

```bash
# Fazer backup
sudo -u multimax /opt/multimax/deploy/scripts/db-manager.sh backup

# Parar app
sudo systemctl stop multimax

# Atualizar código
cd /opt/multimax
# ... (atualizar arquivos)

# Reiniciar
sudo systemctl start multimax
```

---

## Modo de Manutenção

Para bloquear acesso e mostrar página estática:

```bash
# Ativar
echo "MAINTENANCE_MODE=true" | sudo tee -a /opt/multimax/.env
sudo systemctl restart multimax

# Desativar
sudo sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' /opt/multimax/.env
sudo systemctl restart multimax
```

---

## Troubleshooting

### A aplicação não inicia

```bash
# Checar logs
sudo journalctl -u multimax -n 50

# Testar importação
sudo -u multimax /opt/multimax/venv/bin/python -c "from multimax import create_app; create_app()"

# Verificar permissões
ls -la /opt/multimax/.env
ls -la /var/lib/multimax/
```

### Erro de conexão com banco

```bash
# Testar conexão PostgreSQL
sudo -u multimax psql postgresql://multimax:PASSWORD@localhost/multimax_db

# Verificar DATABASE_URL
sudo cat /opt/multimax/.env | grep DATABASE_URL

# Checar serviço PostgreSQL
sudo systemctl status postgresql
```

### Erro de permissão

```bash
# Corrigir proprietário
sudo chown -R multimax:multimax /opt/multimax
sudo chown -R multimax:multimax /var/lib/multimax

# Corrigir permissões
chmod 755 /opt/multimax
chmod 700 /opt/multimax/.env
chmod 755 /var/lib/multimax
```

### Nginx retorna erro 502 (Bad Gateway)

```bash
# Verificar se a app está rodando
sudo systemctl status multimax

# Verificar porta
sudo netstat -tlnp | grep 5000

# Checar log do Nginx
sudo tail -20 /var/log/nginx/error.log
```

---

## Monitoramento

### Health Check

```bash
# Testar endpoint
curl -I http://localhost:5000/

# Via Nginx
curl -I https://seu-dominio.com/
```

### Recursos

```bash
# CPU e RAM
top -u multimax

# Espaço em disco
df -h /var/lib/multimax/

# Conexões
netstat -tulnp | grep python
```

### Backups Automáticos (cron)

```bash
# Adicionar ao crontab do multimax
sudo -u multimax crontab -e

# Backup diário às 2 AM
0 2 * * * /opt/multimax/deploy/scripts/db-manager.sh backup
```

---

## Segurança

### Checklist de Produção

- [ ] Mudar `SECRET_KEY` em `.env`
- [ ] Usar senha forte para banco de dados
- [ ] Habilitar SSL/TLS com Let's Encrypt
- [ ] Configurar firewall (UFW)
  ```bash
  sudo ufw allow 22/tcp
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable
  ```
- [ ] Desabilitar acesso SSH direto para root
- [ ] Usar chaves SSH em vez de senha
- [ ] Fazer backups regulares
- [ ] Monitorar logs regularmente
- [ ] Usar HTTPS em produção (nunca HTTP)

### Permissões de Arquivo

```bash
# Arquivo .env (contém credenciais)
sudo chmod 600 /opt/multimax/.env

# Venv e código
sudo chmod 755 /opt/multimax

# Data dir
sudo chmod 755 /var/lib/multimax
sudo chmod 700 /var/lib/multimax/backups
```

---

## Estrutura de Diretórios

```
/opt/multimax/                    # Home da aplicação
├── app.py
├── requirements.txt
├── multimax/
├── static/
├── templates/
├── venv/                         # Python virtual environment
├── .env                          # Configuração (NÃO commitar!)
├── deploy/                       # Toda lógica de deploy
│   ├── setup.sh                  # Script principal de instalação
│   ├── scripts/
│   │   ├── app-manager.sh        # Gerencia app (start/stop/status)
│   │   └── db-manager.sh         # Gerencia banco (backup/restore)
│   ├── config/
│   │   └── .env.example          # Template de .env
│   ├── systemd/
│   │   └── multimax.service      # Unit file do systemd
│   └── docs/                     # Documentação

/var/lib/multimax/                # Data directory
├── estoque.db                    # SQLite (se usado)
├── backups/                      # Backups de banco
└── logs/                         # Arquivos de log
```

---

## Suporte e Troubleshooting Adicional

Veja:
- [deploy/docs/NGINX.md](NGINX.md) - Configuração Nginx avançada
- [deploy/docs/SYSTEMD.md](SYSTEMD.md) - Detalhes do systemd
- [deploy/docs/DATABASE.md](DATABASE.md) - Configuração de banco

---

**Última atualização:** 23 de janeiro de 2026  
**Versão:** 3.0.17+
