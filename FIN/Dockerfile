FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1

# Instalar solo dependencias mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/ /app/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python3", "chat_handler.py"]
