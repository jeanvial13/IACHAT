# IACHAT_PRO_v3_final (mínimo estable)

Proyecto mínimo estable listo para Portainer + Docker.
Publica el servicio Flask en el puerto 8080.

## Pasos rápidos

1) Crea un archivo `.env` en la raíz (junto al docker-compose.yml):
   ```
   OPENAI_API_KEY=sk-REEMPLAZA_CON_TU_API_KEY
   OPENAI_MODEL=gpt-4o-mini
   ```

2) Construye/arranca con Docker Compose:
   ```bash
   docker compose up -d --build
   ```

3) Abre en el navegador: http://localhost:8080

## Estructura
```
IACHAT_PRO_v3_final/
├── Dock/
│   └── Dockerfile
├── app/
│   ├── chat_handler.py
│   ├── requirements.txt
│   ├── static/
│   ├── templates/
│   └── uploads/
└── docker-compose.yml
```
