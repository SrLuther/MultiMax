# Dockerfile para MultiMax
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias (gcc, git e bibliotecas para WeasyPrint)
RUN apt-get update && \
    apt-get install -y \
        gcc \
        git \
        libgobject-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libffi-dev \
        shared-mime-info && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

# Cria o diretório de dados se não existir
RUN mkdir -p /app/data

# Define variáveis de ambiente padrão
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DEBUG=false

# Expõe a porta da aplicação
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]







