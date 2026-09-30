# Animall — Estado técnico de trabajo

## Objetivo
Consolidar el proyecto sin cambiar el comportamiento funcional sin una razón explícita.

## Punto de partida auditado
- Backend: FastAPI + SQLAlchemy + Pydantic.
- Frontend: React + Vite.
- Tests backend presentes en `tests/`.
- Hay configuración para Docker/Render/Vercel.

## Problemas prioritarios detectados
1. `frontend/src/App.jsx` concentra demasiadas pantallas y lógica.
2. Alembic es la fuente de migraciones también en deployment. Se eliminó `create_all()` del arranque; el contenedor ejecuta `alembic upgrade head` antes de levantar Uvicorn. Para una base existente sin `alembic_version`, sigue siendo necesario verificar el esquema y respaldar antes de decidir un `stamp`.
3. Los flujos reales de la API ya no modifican el stock directamente desde routers; la operación está centralizada en `app/services/stock.py`. Los seeds pueden modificar stock directamente porque son cargadores de datos, pero mantienen movimientos de auditoría.
4. El manejo de fecha/hora de aplicación está centralizado en `app/core/time.py`; queda pendiente revisar cualquier caso funcional adicional durante la prueba integral.
5. Los importes monetarios del modelo usan `Numeric(14,2)` y los cálculos de negocio usan `Decimal`. Los schemas conservan `float` para mantener el contrato JSON.
6. Seeds/demo pueden ejecutarse al arranque mediante `SEED_ON_START`; el Blueprint de producción lo deja en `false` por defecto.
7. README/AGENTS fueron actualizados; las propuestas OpenSpec históricas se mantienen archivadas para no aparecer como tareas activas.
8. Había archivos generados, bases locales, backups y dependencias instaladas mezclados con el código fuente.

## Reglas para futuras tareas
- No reescribir toda la aplicación.
- No cambiar endpoints o contratos públicos sin justificarlo.
- No borrar código por parecer innecesario: primero verificar referencias y uso.
- Cada refactor debe conservar comportamiento y quedar verificable.
- Trabajar por tareas pequeñas, con revisión después de cada tarea.

## Orden de trabajo
- [x] Fase 0: auditoría y punto de partida.
- [x] Fase 1: definir limpieza segura del proyecto.
- [x] Fase 2: consolidar documentación/configuración.
- [x] Fase 3a: agregar infraestructura de Alembic y migración base verificable.
- [x] Fase 4: centralizar cambios de stock y auditar altas/modificaciones/importación.
- [x] Fase 5a: extraer casos de uso de ventas fuera del router.
- [x] Fase 5b: extraer casos de uso de compras fuera del router.
- [x] Fase 5c: centralizar escrituras de caja.
- [x] Fase 6a: separar App.jsx por features/componentes sin cambiar las rutas del frontend.
- [x] Fase 6b: precisión monetaria y fechas centralizadas.
- [ ] Fase 7: revisión/verificación final. (7a estática y 7b revisión de integración completadas; suite completa pendiente de ejecución en Windows)
- [x] Fase 8: deployment — preparación del contenedor, migraciones al arranque, health check con DB y configuración segura de seed.
- [x] Fase 9: cierre de producción — CORS configurable y actualización de configuración Pydantic.
- [x] Fase 10: calidad y release — CI de backend/frontend y limpieza del paquete de entrega.

## Fase 4 — stock

Los flujos reales de stock de API usan `app/services/stock.py`. Crear/importar productos registra el stock inicial como `AJUSTE`; editar stock registra la diferencia como `AJUSTE`; ventas, cancelaciones y entregas de compras usan operaciones específicas. Los seeds siguen siendo código de carga demo y se revisarán por separado.

## Fase 5a — ventas

`app/services/sales.py` concentra crear/cancelar ventas y su transacción de stock, pagos y caja. `app/routers/orders.py` queda como capa HTTP liviana. Los contratos de las rutas se mantienen.

## Fase 5b — compras

`app/services/purchases.py` concentra crear, editar, entregar, pagar y eliminar compras. `app/routers/compras.py` conserva listados/serialización y actúa como capa HTTP. La entrega sigue usando el servicio de stock.

## Fase 5c — caja

`app/services/cash.py` centraliza la creación/eliminación de movimientos de caja y las escrituras automáticas provenientes de ventas, compras y movimientos de proveedores. `app/routers/caja.py` queda enfocado en HTTP, filtros y serialización.

## Fase 6a — frontend

`frontend/src/App.jsx` bajó de 998 a 51 líneas. Se separaron autenticación, ventas, stock/productos, clientes, proveedores, caja, componentes compartidos, hook `useLoad`, validadores, métodos de pago y estado persistente de ventas. Se verificaron los imports locales; el build completo queda pendiente porque las dependencias del ZIP no contienen el binding nativo requerido por Rolldown en Linux.

## Nota sobre la verificación del ZIP
En el entorno de revisión, `pytest` no pudo importar `app` con el comando directo y el frontend no pudo ejecutar `vite/oxlint` porque los binarios dentro de `node_modules` no tenían permisos de ejecución Linux. Esto no se considera una falla funcional del proyecto hasta volver a verificarlo en el entorno Windows del proyecto.

## Fase 6b — dinero y fechas

Los importes de dominio usan `Numeric(14, 2)` en SQLAlchemy. Los schemas siguen exponiendo `float` para conservar el contrato JSON actual y las operaciones internas convierten a `Decimal` mediante `app/services/money.py`. Se agregó la migración Alembic `7f2b8d5c4e31` y se corrigió `alembic/env.py` para resolver la raíz del proyecto y usar `DATABASE_URL` cuando está definido. Las fechas generadas se centralizan en `app/core/time.py`: se conserva almacenamiento UTC naive por compatibilidad, las fechas de usuario se interpretan en `America/Argentina/Mendoza` y los filtros por día usan los límites locales convertidos a UTC. El frontend usa helpers locales para evitar `toISOString().slice(0, 10)` y para interpretar timestamps UTC del backend.

La eliminación de `Base.metadata.create_all()` del arranque ya quedó resuelta en Fase 8. Para una base existente sin `alembic_version`, sigue siendo obligatorio verificar el esquema y respaldar antes de decidir un `stamp`. Los scripts `seed` no crean el esquema: primero se debe ejecutar Alembic.

## Fase 7a — verificación estática

Se verificó compilación sintáctica de Python (`compileall`), consistencia de Alembic sobre una base SQLite nueva (`upgrade head` + `alembic check`), preservación de datos al convertir columnas monetarias Float→Numeric y ausencia de `datetime.utcnow()`/`toISOString().slice(0, 10)` fuera de utilidades. También se corrigió una llave faltante en el `App.jsx` generado durante la Fase 6a y el import faltante de `useEffect` en `Caja.jsx`. La suite completa de pytest y el build/lint frontend quedan para ejecutarlos en el entorno Windows del proyecto, donde el usuario confirmó que los tests habían pasado previamente.


## Fase 7b — revisión de integración

Se corrigió el filtro por día de `app/routers/orders.py` para usar `local_day_bounds_utc`, igual que caja, compras, movimientos de stock y reportes. Así, las consultas por fecha del frontend representan el día local de Mendoza y no un día UTC implícito.

Se eliminó el script manual `scripts/migrate_pagos_pedido.py`, que había quedado obsoleto después de consolidar el esquema y sus cambios en Alembic. La tabla `pagos_pedido` y su backfill ya pertenecen al historial de migraciones; no queda código de producción que cree ese esquema manualmente.

## Fase 8 — deployment

Se eliminó `Base.metadata.create_all()` del arranque porque Alembic pasa a ser la única fuente de cambios de esquema. El `Dockerfile` ahora incluye `alembic/` y `alembic.ini`, necesarios para ejecutar migraciones dentro del contenedor.

`start.sh` ejecuta `alembic upgrade head` antes de la API y solo carga seeds cuando `SEED_ON_START=true`. Los errores de migración o seed ya no se ocultan. El Blueprint deja `SEED_ON_START=false` para no insertar datos demo automáticamente en producción.

`/health` ahora comprueba también la conexión a la base antes de responder correctamente. Se agregó `.dockerignore` para excluir frontend, tests, bases locales, credenciales y herramientas de desarrollo del contexto de Docker.

Pendiente fuera del código: verificar en la base Neon existente que el esquema real corresponde a la migración inicial antes del primer deploy de esta versión si todavía no existe `alembic_version`.

## Verificación post-Fase 8 — pytest en Windows

La ejecución del usuario sobre el ZIP de Fase 8 dio `144 passed`, `16 failed`, `75 warnings`. Los fallos se concentraron en la adaptación de los tests al cambio `Float -> Numeric/Decimal` y en la serialización de `saldo` de movimientos de proveedor.

Se corrigieron los tres puntos relacionados:
- las factories de tests usan `money()/Decimal` para acumular subtotales de pedidos;
- el test de `aplicar_descuento` compara el valor exacto con `money(999.99)`;
- la salida de movimientos de proveedor convierte los importes calculados a `float` antes de devolverlos, manteniendo el contrato JSON existente.

En el entorno de revisión no se pudo repetir `pytest` porque falta `python-jose` y no hubo acceso de red para instalarlo. `compileall` de `app/` y `tests/` quedó correcto. La verificación final de la suite debe repetirse en Windows.

## Fase 9 — cierre de producción

La política CORS dejó de estar fija en `*`: se puede configurar mediante `CORS_ORIGINS` con uno o varios orígenes separados por comas. El valor por defecto conserva `*` para no romper instalaciones existentes; Render declara la variable como configurable para producción.

La configuración de `Settings` usa `SettingsConfigDict`, eliminando la advertencia de Pydantic por la clase `Config` antigua. No se modificaron endpoints ni contratos de la API.

## Fase 10 — calidad y release

Se agregó `.github/workflows/ci.yml` para validar automáticamente en `main` y en pull requests. El backend instala las dependencias, ejecuta `alembic upgrade head`, `alembic check` y la suite de `pytest`; el frontend ejecuta `npm ci`, `npm run lint` y `npm run build`.

El paquete de entrega no incluye `__pycache__`, archivos `.pyc` ni bases locales generadas por ejecuciones anteriores.


## Cambios solicitados por la dueña

- Ventas: un único bloque de pagos para uno o varios medios; transferencia y Mercado Pago se muestran como QR para nuevos registros. Valores legacy se conservan para datos históricos.
- Clientes: mascotas opcionales (perro/gato y nombre), con soporte para varias mascotas por cliente.
- Distribuidoras: pagos parciales, descuentos aplicados al pago y sugerencia de pronto pago configurable por proveedor.
- Historial: resumen diario y mensual de entrada/salida.
- Productos: margen configurable sobre costo y cálculo automático del precio de venta al crear productos.
- Ventas: se guarda y muestra la vendedora autenticada.
- Migración nueva: `20260930_business_requests`.
