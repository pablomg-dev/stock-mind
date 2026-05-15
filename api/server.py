import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

from agent.db import get_recent_decisions  # noqa: E402

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: list[WebSocket] = []


@app.get("/decisions")
def decisions():
    return get_recent_decisions(20)


@app.get("/config")
def public_config():
    """Modo de trading para el badge del frontend (sin secretos)."""
    return {"mode": os.getenv("MODE", "paper").lower()}


@app.get("/balance")
def balance():
    """Obtiene el balance de Kraken Futures (paper o live según configuración)."""
    try:
        mode = os.getenv("MODE", "paper").lower()
        command = ["kraken", "futures", f"{mode}", "balance", "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": f"Kraken CLI error: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Kraken CLI timeout"}
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await asyncio.sleep(30)
            data = get_recent_decisions(1)
            if data:
                await ws.send_text(json.dumps(data[0]))
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
