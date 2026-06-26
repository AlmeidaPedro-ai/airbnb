# ---------------------------------------------------------------------------- #
# Estágio 1 — build do frontend (React + Vite)                                 #
# ---------------------------------------------------------------------------- #
FROM node:22-slim AS frontend
WORKDIR /build
# Dependências primeiro (camada cacheável) e depois o restante do código.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build && ls -la dist

# ---------------------------------------------------------------------------- #
# Estágio 2 — backend (FastAPI) servindo a API + o build estático do frontend  #
# ---------------------------------------------------------------------------- #
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo \
    FRONTEND_DIST=/app/static

WORKDIR /app

# tzdata para o fuso America/Sao_Paulo; curl para o healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./static
RUN chmod +x /app/start.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT:-8000}/api/health" || exit 1

CMD ["/app/start.sh"]
