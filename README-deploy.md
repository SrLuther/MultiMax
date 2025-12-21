# Pacote de Deploy — MultiMax

## Conteúdo do Pacote
- Código-fonte: `app.py`, `multimax/`, `templates/`, `static/`, `scripts/`
- Arquivo de ambiente: `.env.txt` (cópia exata do ambiente local)
- Dependências: `requirements.txt`
- Documentação: este `README-deploy.md`

## Como Descompactar
1. Transfira o arquivo zip para a VPS, por exemplo: `/tmp/multimax-<versao>-<data>.zip`.
2. No servidor, crie a estrutura padrão:
   - `/opt/multimax/app` — código
   - `/opt/multimax-data` — dados (SQLite por padrão)
3. Descompacte:
   - `unzip /tmp/multimax-<versao>-<data>.zip -d /opt/multimax/app/`

## Pós-Deploy (Configuração)
- Proteja o `.env.txt`:
  - `chmod 600 /opt/multimax/app/.env.txt`
- Opcional: escolha o usuário de serviço (padrão `www-data`):
  - `export SERVICE_USER=www-data`
- Opcional: habilitar Alembic apenas se necessário:
  - `export USE_ALEMBIC=true`

## Dependências Externas
- Sistema: `python3`, `python3-venv`, `nginx`, `git`
- Python: instalar via `requirements.txt`

## Deploy Automatizado
- Execute no servidor:
  - `ENV_SRC=/opt/multimax/app/.env.txt /opt/multimax/app/scripts/deploy_vps.sh /tmp/multimax-<versao>-<data>.zip`

## Verificação do Funcionamento
- Health check: `curl -f http://localhost/health`
- Acesso web (default): `http://<host>/`
- Logs:
  - `sudo journalctl -u multimax -n 100 --no-pager`

## Estrutura Resultante
- `/opt/multimax/app` — aplicação
- `/opt/multimax-data/estoque.db` — banco (SQLite)

## Observações
- O arquivo `.env.txt` é copiado exatamente do ambiente local e deve permanecer privado.
- Em produção pública, configure TLS no Nginx (certificados válidos).
