# Animall — Instrucciones para agentes

## Objetivo
Mantener y mejorar Animall sin alterar funcionalidades existentes salvo que la tarea lo pida explícitamente.

## Stack
- Backend: FastAPI + SQLAlchemy + Pydantic.
- Frontend: React + Vite.
- Base local: SQLite. Producción: Postgres mediante `DATABASE_URL`.
- Tests: pytest + httpx.

## Reglas de negocio críticas
- No eliminar productos que tengan historial de ventas: usar `activo=False`.
- Una categoría eliminada no debe dejar productos huérfanos: usar `Sin categoría`.
- Todo cambio de stock debe quedar registrado en `MovimientoStock`; un ajuste manual usa `AJUSTE`.
- Una venta debe validar stock antes de confirmarse.
- Cancelar una venta debe devolver el stock y registrar el movimiento correspondiente.
- Los endpoints protegidos deben conservar su control de roles.
- El backend es la autoridad final para validar reglas de negocio.

## Reglas de implementación
- No reescribir el proyecto completo para una tarea puntual.
- No borrar archivos o funciones sin comprobar sus referencias y su uso.
- No cambiar contratos de API, modelos de datos o comportamiento visible sin indicarlo antes en el plan.
- Mantener las modificaciones pequeñas y relacionadas con la tarea.
- Frontend: las llamadas HTTP pasan por `frontend/src/api.js`.
- Antes de terminar una tarea, ejecutar las verificaciones que correspondan (`pytest`, `npm run lint`, `npm run build`). Si una no puede ejecutarse, informarlo claramente.
- No hacer commits salvo pedido explícito.

## Flujo obligatorio para tareas no triviales
1. Revisar `AGENTS.md`, `README.md` y `ANIMALL_ESTADO.md`.
2. Explicar brevemente qué archivos se tocarán y por qué.
3. Implementar solo el alcance acordado.
4. Verificar regresiones.
5. Actualizar `ANIMALL_ESTADO.md` cuando cambie una decisión o el estado técnico.

## Estructura actual
El proyecto todavía está en una etapa de consolidación. No asumir que toda la estructura objetivo ya existe.
- Backend principal: `app/`
- Routers: `app/routers/`
- Servicios existentes: `app/services/`
- Frontend actual: `frontend/src/`
- Tests: `tests/`
- Scripts auxiliares: `scripts/`

## OpenCode / OpenSpec
`.opencode/`, `.agents/` y `openspec/` son herramientas/documentación locales y no forman parte del código de producción.
No modificar ni eliminar su contenido como parte de una tarea funcional salvo que la tarea lo pida explícitamente.
