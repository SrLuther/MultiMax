# MultiMax - Dockerfile
FROM python:3.11-slim

# Metadados
LABEL maintainer="MultiMax Team"
LABEL description="MultiMax - Plataforma Integrada de Gestão Operacional"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório de dados
RUN mkdir -p /app/data

# Expor porta
EXPOSE 5000

# Comando padrão
CMD ["python", "app.py"]

