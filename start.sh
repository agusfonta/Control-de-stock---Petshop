#!/bin/sh
set -e

echo "Aplicando migraciones Alembic..."
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "SEED_ON_START=true -> python -m app.seed (solo si la DB está vacía)"
  python -m app.seed
  echo "SEED_ON_START=true -> python -m app.seed_demo_ux (solo si no existe DEMO-*)"
  python -m app.seed_demo_ux
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
