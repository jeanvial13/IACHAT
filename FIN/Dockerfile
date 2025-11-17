FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \    build-essential \    libxml2 \    libxslt1.1 \    libjpeg62-turbo \    libpng-dev \    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/ /app/

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python3", "chat_handler.py"]
