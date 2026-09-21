# PetShop Stock API 🐾 — Ani Mall
Demo local (sin Docker): `pip install -r requirements.txt; python -m app.seed; uvicorn app.main:app --reload`
Docs: http://127.0.0.1:8000/docs | Health: `/health`
Frontend: `cd frontend; npm.cmd install; npm.cmd run dev` → http://127.0.0.1:5173 (login admin/admin123 del seed)
Prod con Docker: `docker compose up --build`

## Flujo demo
1. Login admin/admin123 (o POST /auth/register para el primer usuario si la DB está vacía)
2. POST /categorias, POST /productos (categorías opcionales, sku único)
3. POST /clientes
4. POST /pedidos (descuentos combinados linea+pedido, valida stock, error 422 si sin stock)
5. PATCH /pedidos/{id}/cancelar devuelve stock
6. GET /productos?stock_bajo=true | GET /stock/movimientos?fecha=YYYY-MM-DD | GET /reportes/ventas?fecha=YYYY-MM-DD
7. Import CSV: POST /productos/import-csv con plantilla_productos.csv (crea categorías faltantes)

## Reglas de negocio
- Producto puede quedar **Sin categoría** (ej: se borró su categoría); se reasigna con PATCH /productos/{id} {categoria_ids: [...]}
- No se puede eliminar un producto con ventas: desactivarlo en su lugar
- Solo admin elimina categorías/productos y crea usuarios; vendedor opera ventas y stock

## Checklist producción
1. Copiar `.env.example` a `.env` y definir `SECRET_KEY` largo y único + `DATABASE_URL` de Postgres
2. `docker compose up --build` (crea DB + admin via seed solo si está vacía: admin/admin123 → **cambiar contraseña**)
3. Crear usuarios vendedores desde la pestaña Usuarios (solo admin)
4. Verificar `/health` y login en frontend con `VITE_API_URL` apuntando al servidor
