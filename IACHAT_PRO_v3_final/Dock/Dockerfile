# -----------------------------
# Imagen base ligera de Python
# -----------------------------
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación
COPY app /app

# Copia el archivo de dependencias (si está fuera del directorio /app)
COPY app/requirements.txt /app/requirements.txt

# -----------------------------
# Instalación de dependencias
# -----------------------------
RUN apt-get update && \
    apt-get install -y build-essential && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------
# Expone el puerto que usará Flask/FastAPI
# -----------------------------
EXPOSE 8080

# -----------------------------
# Variables de entorno opcionales
# -----------------------------
ENV TZ=America/Mexico_City
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Comando de arranque
# -----------------------------
# Ejecuta el servidor Flask principal de tu app
# Asegúrate de que "chat_handler.py" tenga:
#   app.run(host="0.0.0.0", port=8080)
CMD ["python", "chat_handler.py"]
