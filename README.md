# Animall — Control de stock y ventas 🐾

Aplicación web para gestionar productos, stock, clientes, proveedores, compras, ventas y caja de un pet shop.

## Tecnologías

- Backend: FastAPI, SQLAlchemy, Pydantic.
- Frontend: React + Vite.
- Desarrollo local: SQLite.
- Producción: PostgreSQL mediante `DATABASE_URL`.
- Tests backend: pytest + httpx.

## Estructura

```text
app/          Backend FastAPI
frontend/     Aplicación React
tests/         Tests del backend
scripts/      Scripts auxiliares
```

El proyecto está en proceso de consolidación. Algunas partes todavía necesitan refactorización; no se debe asumir que la estructura actual es la estructura definitiva.

## Desarrollo local

### Backend

Crear/activar un entorno virtual e instalar dependencias:

```bash
pip install -r requirements.txt
```

Para una demo local con SQLite:

```bash
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Alembic administra el esquema. Los comandos `seed` cargan datos de demostración y no crean tablas.

API: `http://127.0.0.1:8000`

Swagger: `http://127.0.0.1:8000/docs`

Health: `http://127.0.0.1:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://127.0.0.1:5173`

El frontend usa `VITE_API_URL` para indicar la URL del backend. Ver `frontend/.env.example`.

## Migraciones

Aplicar todas las migraciones pendientes:

```bash
alembic upgrade head
```

Comprobar que el modelo y las migraciones están sincronizados:

```bash
alembic check
```

En una base existente de producción, no ejecutar un `stamp` a ciegas: primero hay que respaldar la base y confirmar que su esquema corresponde a la migración inicial.

## Docker

Para desarrollo con Docker:

```bash
docker compose up --build
```

## Producción

El backend se despliega como servicio web Docker. La base de datos se proporciona mediante `DATABASE_URL`; el proyecto no debe asumir que Render crea una base PostgreSQL automáticamente.

Al arrancar el contenedor se ejecuta `alembic upgrade head` antes de levantar la API. En una base de producción existente que todavía no tenga `alembic_version`, primero hay que hacer un backup y verificar su esquema antes de decidir un `stamp`; no ejecutar `alembic stamp` a ciegas.

`SEED_ON_START` queda desactivado por defecto en el Blueprint de producción. Activarlo es una decisión explícita para cargar datos demo; nunca usar `--reset` contra la base real.

El frontend puede desplegarse por separado y debe apuntar mediante `VITE_API_URL` a la URL pública del backend.

Nunca usar la `SECRET_KEY` de ejemplo en producción.

`CORS_ORIGINS` permite indicar uno o varios orígenes separados por comas. En producción conviene configurar la URL pública de Vercel en Render; si se omite, se mantiene `*` por compatibilidad.

## Reglas funcionales importantes

- Un producto vendido no se elimina físicamente; se desactiva.
- El stock debe quedar auditado mediante movimientos.
- Una venta valida stock antes de confirmarse.
- Una cancelación devuelve stock.
- Las validaciones del backend son obligatorias aunque exista validación en el frontend.

## Estado del proyecto

Ver [`ANIMALL_ESTADO.md`](./ANIMALL_ESTADO.md) para el diagnóstico técnico y el orden de refactorización.

## CI

GitHub Actions valida cada push a `main` y cada pull request. Se comprueban migraciones y tests del backend, además de lint y build del frontend.
