#!/usr/bin/env bash
set -Eeuo pipefail

############################################
# METADADOS
############################################
APP_NAME="multimax"
SERVICE_NAME="multimax"
SERVICE_USER="${SERVICE_USER:-www-data}"

BASE_DIR="/opt/multimax"
APP_DIR="${BASE_DIR}/app"
VENV_DIR="${BASE_DIR}/venv"
LOG_DIR="${BASE_DIR}/logs"
BACKUP_DIR="${BASE_DIR}/backups"

DATA_DIR="/opt/multimax-data"
DB_FILE="estoque.db"

ENV_FILE="${APP_DIR}/.env.txt"
PKG_PATH="${1:-}"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/deploy-${TS}.log"

############################################
# BOOTSTRAP
############################################
mkdir -p "${APP_DIR}" "${VENV_DIR}" "${LOG_DIR}" "${BACKUP_DIR}" "${DATA_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "==> MultiMax VPS iniciado em ${TS}"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

############################################
# DEPENDÊNCIAS DO SISTEMA (FORÇADO)
############################################
echo "==> Instalando dependências do sistema"

if have_cmd apt-get; then
  sudo apt-get update -y
  sudo apt-get install -y --reinstall \
    python3 python3-venv python3-dev build-essential \
    git curl unzip tzdata pkg-config \
    nginx \
    libpq-dev libjpeg-dev libpng-dev libfreetype6-dev \
    ghostscript fonts-dejavu-core
fi

############################################
# FIREWALL
############################################
detect_firewall() {
  if have_cmd ufw; then echo "UFW"
  elif have_cmd firewall-cmd; then echo "FIREWALLD"
  elif have_cmd iptables; then echo "IPTABLES"
  else echo "NONE"
  fi
}

echo "==> Configurando firewall"
FW="$(detect_firewall)"

case "${FW}" in
  UFW)
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    sudo ufw reload
    ;;
  FIREWALLD)
    sudo systemctl enable firewalld --now
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
    ;;
  IPTABLES)
    for p in 22 80 443; do
      sudo iptables -C INPUT -p tcp --dport $p -j ACCEPT 2>/dev/null || \
      sudo iptables -A INPUT -p tcp --dport $p -j ACCEPT
    done
    sudo iptables-save
    ;;
  NONE)
    echo "⚠️ Nenhum firewall detectado"
    ;;
esac

############################################
# PYTHON / VENV (RESET TOTAL)
############################################
echo "==> Resetando virtualenv"
rm -rf "${VENV_DIR}"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

pip install --no-cache-dir --upgrade pip wheel setuptools

############################################
# DEPLOY DO CÓDIGO
############################################
if [ -z "${PKG_PATH}" ]; then
  echo "❌ Pacote de deploy não informado"
  exit 1
fi

echo "==> Extraindo pacote ${PKG_PATH}"
TMP_EXTRACT_DIR="${APP_DIR}/.extract-${TS}"
mkdir -p "${TMP_EXTRACT_DIR}"

case "${PKG_PATH}" in
  *.zip)
    unzip -q -o "${PKG_PATH}" -d "${TMP_EXTRACT_DIR}"
    ;;
  *.tar.gz|*.tgz)
    tar -xzf "${PKG_PATH}" -C "${TMP_EXTRACT_DIR}"
    ;;
  *.tar.xz|*.txz)
    tar -xJf "${PKG_PATH}" -C "${TMP_EXTRACT_DIR}"
    ;;
  *.tar.bz2|*.tbz2)
    tar -xjf "${PKG_PATH}" -C "${TMP_EXTRACT_DIR}"
    ;;
  *)
    # Tenta extrair como tar genérico; se falhar, acusa formato inválido
    if ! tar -xf "${PKG_PATH}" -C "${TMP_EXTRACT_DIR}" 2>/dev/null; then
      echo "❌ Formato de pacote não suportado: ${PKG_PATH}"
      exit 1
    fi
    ;;
esac

# Move o conteúdo extraído para o diretório da aplicação (flatten se houver pasta raiz única)
shopt -s dotglob nullglob
ROOTS=("${TMP_EXTRACT_DIR}"/*)
if [ ${#ROOTS[@]} -eq 1 ] && [ -d "${ROOTS[0]}" ]; then
  mv "${ROOTS[0]}"/* "${APP_DIR}/"
else
  mv "${TMP_EXTRACT_DIR}"/* "${APP_DIR}/"
fi
shopt -u dotglob nullglob
rm -rf "${TMP_EXTRACT_DIR}"

############################################
# DEPENDÊNCIAS PYTHON (FORÇADO)
############################################
echo "==> Instalando dependências Python"
pip install --no-cache-dir --force-reinstall -r "${APP_DIR}/requirements.txt"
pip install --no-cache-dir --force-reinstall gunicorn alembic python-dotenv

############################################
# VERIFICAÇÃO DE DEPENDÊNCIAS
############################################
echo "==> Verificando dependências críticas"

python <<'PY'
mods = [
  "flask","flask_sqlalchemy","flask_login",
  "sqlalchemy","alembic","psycopg",
  "reportlab","matplotlib","PIL",
  "qrcode","openpyxl","requests","waitress","gunicorn"
]
for m in mods:
    __import__(m)
    print(f"✔ {m}")
PY

############################################
# ENV
############################################
ENV_SRC="${ENV_SRC:-${2:-}}"
if [ -f "${ENV_FILE}" ]; then
  echo "==> Mantendo .env.txt existente no APP"
elif [ -n "${ENV_SRC}" ] && [ -f "${ENV_SRC}" ]; then
  echo "==> Copiando .env.txt a partir de ${ENV_SRC}"
  cp "${ENV_SRC}" "${ENV_FILE}"
elif [ -f "${APP_DIR}/.env.txt" ]; then
  echo "==> .env.txt encontrado no pacote (mantendo)"
else
  echo "❌ .env.txt não encontrado. Forneça ENV_SRC (2º argumento) apontando para o arquivo desta máquina."
  exit 2
fi

export $(grep -v '^#' "${ENV_FILE}" | xargs)

# Protege o arquivo de ambiente
chmod 600 "${ENV_FILE}" || true

############################################
# ALEMBIC (AUTO TOTAL)
############################################
echo "==> Garantindo banco e schema"
mkdir -p "${DATA_DIR}"

USE_ALEMBIC="${USE_ALEMBIC:-false}"
if [ "${USE_ALEMBIC}" = "true" ]; then
  if [ ! -d "${APP_DIR}/alembic" ]; then
    pushd "${APP_DIR}" >/dev/null
    alembic init alembic
    popd >/dev/null
  fi

  cat > "${APP_DIR}/alembic/env.py" <<'PY'
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv
import os
load_dotenv(".env.txt")
from multimax import db
target_metadata = db.metadata
def run():
    engine = engine_from_config(
        {"sqlalchemy.url": os.getenv("SQLALCHEMY_DATABASE_URI")},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
run()
PY

  pushd "${APP_DIR}" >/dev/null
  alembic revision --autogenerate -m "auto-${TS}" || true
  alembic upgrade head
  popd >/dev/null
fi

############################################
# SYSTEMD + GUNICORN
############################################
id -u "${SERVICE_USER}" >/dev/null 2>&1 && sudo chown -R "${SERVICE_USER}:${SERVICE_USER}" "${BASE_DIR}" "${DATA_DIR}" || true
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

sudo bash -c "cat > '${UNIT_FILE}' <<EOF
[Unit]
Description=MultiMax Service
After=network.target

[Service]
User=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

############################################
# NGINX
############################################
echo "==> Configurando Nginx"

sudo bash -c "cat > /etc/nginx/sites-available/multimax <<EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location /static {
        alias ${APP_DIR}/static;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"

sudo ln -sf /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/multimax
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

############################################
# HEALTH CHECK
############################################
sleep 3
curl -f http://localhost/health && echo "✔ HEALTH OK"

echo "==> DEPLOY FINALIZADO COM SUCESSO"
echo "Log: ${LOG_FILE}"
