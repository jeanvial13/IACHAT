# ---------------------------------------------------------
# STAGE 1 — Build environment (compilar libs pesadas)
# ---------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1

# Instalar dependencias necesarias para compilar reportlab, openpyxl, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY app/ /build/

RUN pip install --upgrade pip setuptools wheel
RUN pip install --prefix=/install -r requirements.txt


# ---------------------------------------------------------
# STAGE 2 — Final image (clean, optimized)
# ---------------------------------------------------------
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

# Instalar las librerías mínimas necesarias en runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar solo el código + librerías necesarias (limpio)
COPY --from=builder /install /usr/local
COPY --from=builder /build /app

# Crear uploads y logs
RUN mkdir -p /app/uploads && mkdir -p /app/logs

EXPOSE 8080

# HEALTHCHECK profesional
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
   CMD wget -qO- http://localhost:8080/login || exit 1

CMD ["python3", "chat_handler.py"]
