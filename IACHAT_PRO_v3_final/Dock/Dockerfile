FROM python:3.11-slim

WORKDIR /app

COPY app /app

COPY app/requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y build-essential &&     pip install --no-cache-dir -r requirements.txt &&     apt-get remove -y build-essential && apt-get autoremove -y && apt-get clean &&     rm -rf /var/lib/apt/lists/*

EXPOSE 8080

ENV TZ=America/Mexico_City
ENV PYTHONUNBUFFERED=1

CMD ["python", "chat_handler.py"]
