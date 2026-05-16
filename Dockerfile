FROM python:3.11-slim

LABEL maintainer="Marcelo Marins <marcelom@example.com>"
LABEL description="Finance Data Pipeline — AWS S3 + PostgreSQL"

# Evita prompts interativos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copia código-fonte
COPY src/ ./src/
COPY sql/ ./sql/
COPY .env.example .env.example

# Cria diretórios de dados
RUN mkdir -p data/raw data/processed

# Executa o pipeline completo por padrão
CMD ["python", "src/run_pipeline.py"]
