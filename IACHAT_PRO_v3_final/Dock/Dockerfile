FROM python:3.11-slim

WORKDIR /app

# copy app files
COPY app /app

RUN apt-get update && apt-get install -y build-essential     && pip install --no-cache-dir -r requirements.txt     && apt-get remove -y build-essential && apt-get autoremove -y && apt-get clean

EXPOSE 8080

CMD ["python", "chat_handler.py"]
