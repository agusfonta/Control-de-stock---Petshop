# Animall — Instrucciones para Agentes

> v1 lite (sin `knowledge-base/` ni `CHANGES.md` todavía). Es lo PRIMERO que todo agente lee al entrar al repo. Mantener corto y operativo.

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| Backend | FastAPI + Uvicorn | 0.116.1 / 0.35.0 |
| ORM / Migraciones | SQLAlchemy / Alembic | 2.0.43 / 1.16.5 |
| Validación | Pydantic v2 + pydantic-settings | 2.11.7 / 2.10.1 |
| Auth | python-jose HS256 + passlib bcrypt | 3.5.0 / 1.7.4 |
| DB | SQLite demo (`petshop.db`) / Postgres 16 en Docker | — |
| Frontend | React + Vite | 19.2.8 / 8.3.0 |
| Tests | pytest + httpx | 8.4.1 / 0.28.1 |

## Comandos

```bash
# Backend demo local
pip install -r requirements.txt; python -m app.seed; uvicorn app.main:app --reload
# Docs: http://127.0.0.1:8000/docs | Health: /health

# Frontend
cd frontend; npm.cmd install; npm.cmd run dev  # -> http://127.0.0.1:5173, VITE_API_URL o http://127.0.0.1:8000
# Prod
docker compose up --build
# Nube (tablet): Render crea API + Postgres gratis desde `render.yaml:1`
# (DB auto, `SECRET_KEY` generado, seed + demo UX en primer arranque vía `start.sh:4`).
# Front en Vercel con `VITE_API_URL=https://<tu-api>.onrender.com` (`frontend/.env.example:2`).
# `app/core/database.py:7` normaliza `postgres://` de Render a `postgresql+psycopg2://`.
# Seed reset (borra todo)
python -m app.seed --reset
```

Env: copiar `.env.example` a `.env`. Default `DATABASE_URL=sqlite:///./petshop.db`, `SECRET_KEY` demo en `app/core/config.py:9`. Seed crea `admin/admin123` + `vendedora/demo1234` (`app/seed.py:188`).

## Estructura

- `app/main.py:16` — FastAPI + CORS + routers
- `app/models.py:1` — Categoria, Producto (+`producto_categoria`, +`producto_proveedor`, `proveedor_id` principal), Cliente, Pedido/DetallePedido (`MetodoPago`: efectivo/tarjeta-legacy/transferencia/mercadopago/debito/credito), MovimientoStock, Proveedor (+`alias`, `dias_entrega`), MovimientoProveedor (cta.cte 001-004), MovimientoCaja (ENTRADA/SALIDA por medio), User
- `app/schemas.py:1` — Pydantic v2 estricta
- `app/routers/` — `auth.py`, `categories.py`, `products.py`, `customers.py`, `orders.py` (ventas escriben en caja), `inventory.py` (stock + `/proveedores` con cta.cte + `/reportes`), `caja.py` (caja diaria, gastos manuales)
- `app/core/` — `config.py`, `database.py`, `security.py` | `app/deps.py:23` — `require_roles()`
- `app/services/discounts.py` — `aplicar_descuento`
- `frontend/src/api.js:1` — único cliente HTTP (Bearer, maneja 401/403) | `frontend/src/App.jsx:13` — tabs Principal / Stock / Clientes / Distribuidoras / Historial (caja). Pedidos del cliente en modal; categoría nueva desde el filtro de Stock; cuenta primero en Distribuidoras; sin tab Usuarios (gestión por API) | `frontend/src/index.css` — un solo layout compu+tablet apaisada: tablas nuevas van en `.tbl-wrap`, táctil solo bajo `@media (pointer:coarse)`

## Skills Disponibles

En `.agents/skills/` (flujo OpenSpec):

| Rol | Skills que carga |
|-----|------------------|
| Orquestación / SDD | `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-update-change`, `openspec-sync-specs`, `openspec-archive-change` |

> Sin `knowledge-base/` ni `CHANGES.md` — correr `kb-creator` + `roadmap-generator` para versión canónica completa.

## Reglas Duras (específicas del proyecto)

- NUNCA borrar producto con ventas → desactivar con `activo=False` (`app/models.py:73`).
- NUNCA dejar producto huérfano al borrar categoría → queda `Sin categoría`, reasignar con `PATCH /productos/{id} {categoria_ids:[...]}`.
- NUNCA cambiar `stock` sin `MovimientoStock` (`INGRESO`, `EGRESO_VENTA`, `DEVOLUCION_CANCEL`) con `stock_anterior/nuevo` (`app/models.py:119`).
- NUNCA crear pedido sin validar stock → 422 si falta; cancelar solo vía `PATCH /pedidos/{id}/cancelar` (devuelve stock).
- NUNCA exponer endpoint sensible sin `require_roles()` — solo `admin` borra categorías/productos y crea usuarios (`app/deps.py:23`, `frontend/src/api.js:28`); `vendedor` opera ventas/stock.
- NUNCA usar `SECRET_KEY` demo en prod → exigir `.env` largo y único.
- NUNCA saltar validación Pydantic: `sku` único, `precio_venta>0`, `descuento porcentaje<=100`, `ningun→valor 0`, `imagen_url` solo `http(s)`, `email/dni` únicos (`app/schemas.py:9`).
- NUNCA llamar fetch directo en frontend → usar `api` de `frontend/src/api.js:43`.

## Flujo de Trabajo

1. Leer sección relevante de este archivo + `README.md` antes de codear.
2. Backend: router + schema + servicio; Frontend: `api.js` + componente en `App.jsx`.
3. Verificar con ejecución (`uvicorn` / `vite dev` / `pytest`) antes de afirmar.
4. Referenciar `archivo:línea` en respuestas. No crear archivos nuevos si basta editar. No commitear/buildear sin pedido.
