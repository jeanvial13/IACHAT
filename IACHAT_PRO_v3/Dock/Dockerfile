FROM python:3.11-slim

WORKDIR /app

# Copia todo el contenido de la carpeta app
COPY ../app /app

RUN pip install --no-cache-dir flask flask-cors openai

EXPOSE 8080

CMD ["python", "chat_handler.py"]
