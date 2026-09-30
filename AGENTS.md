# Animall — Instrucciones para Agentes

> Configuración OpenCode profesional. Reglas generales y permanentes únicamente.

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI + SQLAlchemy 2 + Pydantic 2 (SQLite/Postgres) |
| Frontend | React 19 + Vite (App.jsx único) |
| Tests | pytest + httpx |
| Auth | python-jose HS256 + passlib bcrypt |

## Reglas Duras (inmutables)

- **NUNCA** borrar producto con ventas → desactivar `activo=False`
- **NUNCA** dejar producto huérfano al borrar categoría → reasignar a `Sin categoría`
- **NUNCA** cambiar `stock` sin `MovimientoStock` (`INGRESO`, `EGRESO_VENTA`, `DEVOLUCION_CANCEL`) con `stock_anterior/nuevo`
- **NUNCA** crear pedido sin validar stock → 422 si falta
- **NUNCA** exponer endpoint sensible sin `require_roles()` (admin/vendedor)
- **NUNCA** usar `SECRET_KEY` demo en producción
- **NUNCA** saltar validación Pydantic (sku único, precio>0, descuento≤100, URLs http(s), email/dni únicos)
- **NUNCA** llamar fetch directo en frontend → usar `api` de `frontend/src/api.js`
- **SIEMPRE** UX/UI frontend profesional: clara, consistente, responsive, funcional, con feedback de carga/error/vacío, accesibilidad básica, respetando patrones visuales existentes, sin elementos innecesarios

## Flujo de Trabajo

1. Leer `AGENTS.md` + `README.md` antes de codear
2. Backend: router + schema + servicio | Frontend: `api.js` + componente en `App.jsx`
3. Verificar con `pytest` y `npm run lint` antes de afirmar
4. Referenciar `archivo:línea` | No crear archivos si basta editar | No commitear sin pedido

## Agentes OpenCode (definidos en `opencode.json`)

| Agente | Rol | Permisos |
|--------|-----|----------|
| `orchestrator` | Coordinación, alcance, delegación | Solo lectura + Task tool |
| `architect` | Análisis, planificación, diseño | Solo lectura |
| `programmer` | Implementación backend/frontend | Lectura + Escritura |
| `tester` | Verificación, tests, calidad | Lectura + Tests |

## Skills del proyecto (`.opencode/skills/`)

- `openspec-*` (6 skills): flujo OPSX completo (explore, propose, apply, update, sync, archive)