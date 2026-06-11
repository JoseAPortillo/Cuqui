# ── Stage 1: Build frontend ─────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

# System deps: ffmpeg needed by faster-whisper for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies (base + ASR + LLM extras)
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.34" \
    "websockets>=14.0" \
    "pydantic>=2.0" \
    "python-multipart>=0.0.18" \
    "faster-whisper>=1.0" \
    "openai>=1.0" \
    "pywebpush>=1.14" \
    "cryptography>=42.0"

# Copy backend source (excluding tests)
COPY backend/cuqui/ ./cuqui/

# Copy frontend production build from Stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# ── Runtime configuration ──────────────────────────────────────────────────
ENV CUQUI_SERVE_FRONTEND=1 \
    CUQUI_PORT=8000 \
    CUQUI_RELOAD=0 \
    HF_HOME=/app/data/hf_cache

# ── Non-root user (security best practice) ───────────────────────────────
RUN addgroup --system --gid 1001 cuqui && \
    adduser --system --uid 1001 --ingroup cuqui --no-create-home cuqui && \
    mkdir -p /app/data/hf_cache && \
    chown -R cuqui:cuqui /app/data

EXPOSE 8000

USER cuqui

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

ENTRYPOINT ["uvicorn", "cuqui.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
