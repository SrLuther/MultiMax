# Instalação MultiMax em VPS

## Requisitos

- Python 3.8 ou superior
- pip
- Banco de dados SQLite (padrão) ou PostgreSQL/MySQL (opcional)

## Passos de Instalação

### 1. Extrair o arquivo ZIP

```bash
unzip multimax-vps-deploy.zip
cd MultiMax-DEV
```

### 2. Criar ambiente virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente (opcional)

Crie um arquivo `.env` na raiz do projeto:

```env
FLASK_ENV=production
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///multimax.db
HOST=0.0.0.0
PORT=5000
DEBUG=false
```

### 5. Inicializar o banco de dados

```bash
python -c "from multimax import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 6. Executar a aplicação

#### Opção 1: Modo desenvolvimento
```bash
python app.py
```

#### Opção 2: Usando Waitress (produção)
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

#### Opção 3: Usando Gunicorn (Linux)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 7. Configurar como serviço systemd (Linux)

Crie o arquivo `/etc/systemd/system/multimax.service`:

```ini
[Unit]
Description=MultiMax Application
After=network.target

[Service]
Type=simple
User=seu-usuario
WorkingDirectory=/caminho/para/MultiMax-DEV
Environment="PATH=/caminho/para/venv/bin"
ExecStart=/caminho/para/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Ativar o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable multimax
sudo systemctl start multimax
```

### 8. Configurar Nginx como proxy reverso (opcional)

Adicione ao `/etc/nginx/sites-available/multimax`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ativar:
```bash
sudo ln -s /etc/nginx/sites-available/multimax /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Estrutura de Arquivos

```
MultiMax-DEV/
├── app.py                 # Arquivo principal
├── requirements.txt       # Dependências Python
├── multimax/             # Código da aplicação
│   ├── __init__.py       # Inicialização Flask
│   ├── models.py         # Modelos de banco de dados
│   └── routes/           # Rotas da aplicação
├── templates/            # Templates HTML
├── static/               # Arquivos estáticos (CSS, JS, imagens)
└── .env                  # Variáveis de ambiente (criar)
```

## Primeiro Acesso

1. Acesse `http://seu-servidor:5000`
2. Crie uma conta de administrador através do formulário de registro
3. Faça login e configure o sistema

## Backup do Banco de Dados

```bash
# SQLite
cp multimax.db backup_multimax_$(date +%Y%m%d).db

# PostgreSQL
pg_dump -U usuario -d multimax > backup_$(date +%Y%m%d).sql
```

## Atualização

1. Fazer backup do banco de dados
2. Extrair nova versão do ZIP
3. Instalar novas dependências: `pip install -r requirements.txt`
4. Reiniciar o serviço: `sudo systemctl restart multimax`

## Suporte

Para problemas ou dúvidas, consulte a documentação ou entre em contato com o suporte.

