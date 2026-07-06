# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve static ─────────────────────────────────
FROM python:3.11-slim

# Install build deps for heavy Python packages (torch, transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces: create user 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BTA_VERSION=3.3

WORKDIR $HOME/app

# Python deps (includes torch, transformers, duckduckgo-search for chat + agent)
COPY --chown=user requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (includes routes/, ml/, mlops/, etl/, enrichment/, utils.py)
COPY --chown=user backend/ ./backend/

# Create data directory
RUN mkdir -p ./data && chown user:user ./data

# Copy React build from stage 1
COPY --from=frontend-builder --chown=user /frontend/dist ./static/

# Copy tests (optional — not loaded at runtime)
COPY --chown=user tests/ ./tests/

USER user

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
