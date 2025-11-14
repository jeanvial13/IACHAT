FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (if we ever need to add more parsers)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app ./app

# Install Python dependencies
RUN pip install --no-cache-dir -r app/requirements.txt

EXPOSE 8080

CMD ["python", "app/chat_handler.py"]
