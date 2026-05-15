# StockMind

Agente autónomo de trading de **xStocks** (Kraken CLI + Gemini 2.5 Flash) con dashboard en React.

## Requisitos

- Python **3.11+**
- [Kraken CLI](https://github.com/krakenfx/kraken-cli) instalado y en el `PATH`
- Node.js **18+** (para el frontend)
- API key de [Google AI Studio](https://aistudio.google.com/app/apikey) (Gemini)

## Configuración

En **Windows PowerShell** (incluida 5.x) no uses `&&` para encadenar: ejecutá **un comando por línea**, o en una sola línea usá `;` (por ejemplo `cd frontend; npm install`).

1. Copiá el ejemplo de entorno y completá las variables:

   **PowerShell (raíz del repo):**

   ```powershell
   Copy-Item .env.example .env
   ```

   En bash (Linux/macOS): `cp .env.example .env`

2. Instalá dependencias Python (recomendado: entorno virtual):

   **PowerShell:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   Si la activación falla por política de ejecución: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (una vez).

3. Instalá dependencias del frontend:

   **PowerShell:**

   ```powershell
   Set-Location frontend
   npm install
   ```

   Para volver a la raíz después: `Set-Location ..`

## Cómo ejecutar

Desde la **raíz del repositorio** (`StockMind/`):

| Componente | Comando (PowerShell: uno por línea) |
|------------|-------------------------------------|
| Agente (loop) | `python -m agent.main` |
| API (FastAPI) | `uvicorn api.server:app --reload --port 8000` |
| Dashboard | `Set-Location frontend` luego `npm run dev` |

Equivalente en una sola línea (válido en PowerShell): `Set-Location frontend; npm run dev`

El frontend en desarrollo usa **proxy** hacia `http://127.0.0.1:8000` para `/decisions`, `/config` y `/ws`. Si corrés el build estático sin proxy, definí `VITE_API_URL` (por ejemplo `http://localhost:8000`).

Opcional: variable `STOCKMIND_DB_PATH` apunta al archivo SQLite compartido entre el agente y la API (por defecto: `stockmind.db` en la raíz del repo).

## Modo paper vs live

El archivo `.env` define `MODE=paper` o `MODE=live`. El dashboard muestra un badge **Paper** o **Live** según `GET /config` (lee el mismo `.env` que la API).

## Estructura

- `agent/` — señales, Gemini, ejecución Kraken, SQLite, loop principal
- `api/` — REST + WebSocket para el frontend
- `frontend/` — Vite + React + Tailwind + Recharts

Las convenciones detalladas del hackathon están en `.cursor/rules/stockmind.mdc`.
