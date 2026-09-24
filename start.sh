#!/bin/sh
# Start para Render: siembra la demo solo si la DB está vacía y levanta la API en $PORT.
set -e
if [ "$SEED_ON_START" = "true" ]; then
  echo "SEED_ON_START=true -> python -m app.seed (solo si vacia)"
  python -m app.seed || echo "WARN: seed fallo, sigo con el arranque"
  echo "SEED_ON_START=true -> python -m app.seed_demo_ux (solo si no hay DEMO-*)"
  python -m app.seed_demo_ux || echo "WARN: seed demo ux fallo, sigo con el arranque"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
