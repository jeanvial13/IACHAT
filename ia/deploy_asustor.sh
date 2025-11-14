#!/bin/sh
echo "=== IACHAT ASUSTOR DEPLOY ==="
echo "1) BUILDING IMAGE..."
docker compose build

echo "2) CREATING FINAL CONTAINER WITH PORT MAPPING..."
docker rm -f iachat_asustor_final 2>/dev/null
docker run -d \
  --name iachat_asustor_final \
  -p 8080:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e OPENAI_MODEL=gpt-4o-mini \
  -v $(pwd)/app/uploads:/app/uploads \
  iachat_asustor_builder:latest

echo "DONE. Open: http://NAS_IP:8080"
