# ---------------------------------------------------------
# BASE IMAGE
# ---------------------------------------------------------
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema para reportlab, docx, pdf, excel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar TODA tu carpeta app (donde está requirements.txt real)
COPY app/ /app/

# Instalar dependencias Python
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Crear carpetas necesarias
RUN mkdir -p /app/uploads && mkdir -p /app/logs

EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
   CMD wget -qO- http://localhost:8080/login || exit 1

CMD ["python3", "chat_handler.py"]
