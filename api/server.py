import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# Global configuration variables
config_leverage: int = int(os.getenv("FUTURES_LEVERAGE", "5"))
config_max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "10")) / 100


class ConfigUpdate(BaseModel):
    leverage: Optional[int] = None
    max_position_pct: Optional[float] = None


@app.get("/decisions")
def decisions():
    return get_recent_decisions(20)


@app.get("/config")
def public_config():
    """Modo de trading y configuración para el frontend (sin secretos)."""
    return {
        "mode": os.getenv("MODE", "paper").lower(),
        "leverage": config_leverage,
        "max_position_pct": round(config_max_position_pct * 100, 1)
    }


@app.post("/config")
def update_config(update: ConfigUpdate):
    """Actualiza leverage y max_position_pct en memoria."""
    global config_leverage, config_max_position_pct
    
    if update.leverage is not None:
        if not 1 <= update.leverage <= 10:
            raise ValueError("Leverage must be between 1 and 10")
        config_leverage = update.leverage
    
    if update.max_position_pct is not None:
        if not 1 <= update.max_position_pct <= 25:
            raise ValueError("Max position percentage must be between 1% and 25%")
        config_max_position_pct = update.max_position_pct / 100
    
    return {
        "leverage": config_leverage,
        "max_position_pct": round(config_max_position_pct * 100, 1)
    }


@app.get("/balance")
def balance():
    """Obtiene el balance de Kraken Futures (paper o live según configuración)."""
    try:
        mode = os.getenv("MODE", "paper").lower()
        command = ["kraken", "futures", f"{mode}", "balance", "-o", "json"]
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout[:200]}")
        print(f"Stderr: {result.stderr[:200]}")
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return {"error": f"Invalid JSON from Kraken CLI: {str(e)}", "raw_output": result.stdout[:500]}
        else:
            return {"error": f"Kraken CLI error (code {result.returncode}): {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Kraken CLI timeout"}
    except FileNotFoundError:
        return {"error": "Kraken CLI not found. Please install Kraken CLI and add it to PATH."}
    except Exception as e:
        print(f"Unexpected error: {e}")
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
