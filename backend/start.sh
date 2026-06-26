#!/usr/bin/env sh
# Entrypoint de produção: aplica migrações, (opcional) seed e sobe a API.
set -e

echo "[start] Aplicando migrações (alembic upgrade head)..."
alembic upgrade head

if [ "$SEED_ON_START" = "true" ]; then
  echo "[start] Executando seed inicial..."
  python -m app.seed || echo "[start] seed falhou/ja aplicado (ignorado)"
fi

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"
echo "[start] Subindo gunicorn em 0.0.0.0:${PORT} (${WORKERS} workers)..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --access-logfile - \
  --error-logfile -
