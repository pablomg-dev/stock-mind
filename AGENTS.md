# StockMind Project Conventions

## Python
- Virtual env: `.venv/` (activar con `source .venv/bin/activate`)
- Dependencias en `requirements.txt`
- El agente se ejecuta con: `python3 agent/main.py`
- API server: `python3 -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000`
- La configuración del proyecto está en `.env`

## Frontend
- React + Vite + TailwindCSS
- Componentes en `frontend/src/components/`
- Ejecutar con: `npm run dev` dentro de `frontend/`
- Endpoints API en `frontend/src/api.js`

## Kraken CLI
- Comandos con prefijo `kraken`
- Datos OHLCV via API REST: `https://futures.kraken.com/api/charts/v1/trade/{symbol}/{resolution}`
- Precio via: `kraken futures ticker <symbol> -o json`

## Base de datos
- SQLite (`stockmind.db`)
- Tablas: trades, reasoning_log, config, error_log, agent_status

## Estilo de código
- Python: sin comentarios en código, tipado con TypedDict
- JSX: componentes funcionales con hooks
- TailwindCSS para estilos, tema oscuro (slate slate-900 slate-800)
