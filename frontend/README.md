# Frontend de Animall

Frontend de la aplicación Animall, construido con React + Vite.

## Comandos

```bash
npm install
npm run dev
npm run lint
npm run build
```

## Configuración

Copiar `frontend/.env.example` a un archivo `.env` local y definir:

```text
VITE_API_URL=http://127.0.0.1:8000
```

Las llamadas HTTP deben centralizarse en `src/api.js`.

La interfaz actual se encuentra principalmente en `src/App.jsx`. Su división progresiva en componentes/features forma parte de la refactorización planificada.
