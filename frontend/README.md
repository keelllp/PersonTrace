# PersonTrace frontend

Vite + React + TypeScript (strict) + Tailwind CSS v4 SPA. Server state lives in
TanStack Query; routing is react-router. See the repo root README for how it
fits together with the FastAPI backend.

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend on :8000
npm test         # vitest
npm run build    # production bundle in dist/ (served by FastAPI when present)
```
