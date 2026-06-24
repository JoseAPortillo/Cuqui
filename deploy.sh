#!/usr/bin/env bash
set -euo pipefail

# ── 1. Instalar Docker ─────────────────────────────────────────────────────
# Necesitamos Docker para construir y ejecutar la app.
# docker.io viene en los repos de Ubuntu.
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2

# Añadir usuario al grupo docker para no usar sudo
sudo usermod -aG docker "$USER"

# Habilitar e iniciar Docker (para que arranque al reiniciar la VM)
sudo systemctl enable --now docker

# ── 2. Clonar repositorio ──────────────────────────────────────────────────
git clone https://github.com/JoseAPortillo/Cuqui.git /home/ubuntu/Cuqui
cd /home/ubuntu/Cuqui

# ── 3. Crear archivo .env ──────────────────────────────────────────────────
# Necesitas pegar tu OPENAI_API_KEY aquí
# (editar con nano .env después)
cat > .env <<'EOF'
OPENAI_API_KEY=pon-tu-key-aqui
EOF

# ── 4. Build y arranque ────────────────────────────────────────────────────
# docker compose build: construye la imagen (frontend + backend)
# docker compose up -d: arranca en segundo plano
docker compose build
docker compose up -d

echo "----------------------------------------"
echo "Despliegue completado!"
echo "La app debería estar corriendo en http://localhost:8000"
echo "Para ver logs: docker compose logs -f"
echo "Para reiniciar: docker compose restart"
echo "----------------------------------------"
