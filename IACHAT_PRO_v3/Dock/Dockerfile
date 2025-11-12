FROM python:3.11-slim

WORKDIR /app

COPY ../app /app

RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=chatgpt_console.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "chatgpt_console.py"]
