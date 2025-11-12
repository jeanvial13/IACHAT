# IACHAT_PRO v3 — Terminal + Proyectos + Créditos + ZIPs

## Despliegue con Portainer
1) Subir repo a GitHub.
2) Portainer → Stacks → Add Stack → Repository
   - Repository URL: https://github.com/<tu_usuario>/IACHAT_PRO_v3.git
   - Compose path: Dock/docker-compose.yml
   - Env vars: OPENAI_API_KEY=sk-..., (opcional) OPENAI_MODEL=gpt-4o
3) Deploy → abrir http://<IP-NAS>:8080

Volúmenes:
- `iachat_data:/data` (persisten proyectos/chats)
- `./app/downloads:/app/downloads` (ZIPs accesibles y persistentes)
