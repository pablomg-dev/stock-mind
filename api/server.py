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

from agent.db import (
    get_recent_decisions,
    get_config_db,
    set_config_db,
    get_agent_status,
    update_agent_status,
    get_recent_trades,
    log_error,
)
from agent.executor import execute_order, get_balance, run_kraken

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: list[WebSocket] = []

# Global configuration variables (fallback to env)
config_leverage: int = int(os.getenv("FUTURES_LEVERAGE", "5"))
config_max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "10")) / 100
config_interval_minutes: int = int(os.getenv("INTERVAL_MINUTES", "15"))


def _load_persistent_config():
    """Load configuration from database on startup."""
    global config_leverage, config_max_position_pct, config_interval_minutes
    try:
        db_config = get_config_db()
        if "leverage" in db_config:
            config_leverage = int(db_config["leverage"])
        if "max_position_pct" in db_config:
            config_max_position_pct = float(db_config["max_position_pct"]) / 100
        if "interval_minutes" in db_config:
            config_interval_minutes = int(db_config["interval_minutes"])
    except Exception as e:
        print(f"Warning: Could not load persistent config: {e}")


_load_persistent_config()


class ConfigUpdate(BaseModel):
    leverage: Optional[int] = None
    max_position_pct: Optional[float] = None
    interval_minutes: Optional[int] = None


@app.get("/health")
def health():
    """Health check endpoint."""
    status = get_agent_status()
    return {
        "status": "ok",
        "agent": status["status"],
        "last_heartbeat": status["last_heartbeat"],
    }


@app.get("/decisions")
def decisions():
    return get_recent_decisions(20)


@app.get("/trades")
def trades():
    return get_recent_trades(50)


@app.get("/status")
def agent_status():
    """Get current agent status from database."""
    return get_agent_status()


@app.get("/config")
def public_config():
    """Modo de trading y configuración para el frontend (sin secretos)."""
    return {
        "mode": os.getenv("MODE", "paper").lower(),
        "leverage": config_leverage,
        "max_position_pct": round(config_max_position_pct * 100, 1),
        "interval_minutes": config_interval_minutes
    }


@app.post("/config")
def update_config(update: ConfigUpdate):
    """Actualiza leverage y max_position_pct en la base de datos."""
    global config_leverage, config_max_position_pct, config_interval_minutes

    if update.leverage is not None:
        if not 1 <= update.leverage <= 10:
            raise ValueError("Leverage must be between 1 and 10")
        config_leverage = update.leverage
        set_config_db("leverage", str(config_leverage))

    if update.max_position_pct is not None:
        if not 1 <= update.max_position_pct <= 25:
            raise ValueError("Max position percentage must be between 1% and 25%")
        config_max_position_pct = update.max_position_pct / 100
        set_config_db("max_position_pct", str(update.max_position_pct))

    if update.interval_minutes is not None:
        if not 5 <= update.interval_minutes <= 60:
            raise ValueError("Interval must be between 5 and 60 minutes")
        config_interval_minutes = update.interval_minutes
        set_config_db("interval_minutes", str(config_interval_minutes))

    return {
        "leverage": config_leverage,
        "max_position_pct": round(config_max_position_pct * 100, 1),
        "interval_minutes": config_interval_minutes
    }


@app.post("/emergency-close")
def emergency_close():
    """Emergency close all open positions."""
    try:
        mode = os.getenv("MODE", "paper").lower()
        ticker = os.getenv("TICKER", "PF_NVDAXUSD")

        # Get current position
        command = ["kraken", "futures", f"{mode}", "positions", "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return {"error": f"Failed to get positions: {result.stderr}"}

        data = json.loads(result.stdout)
        open_positions = []
        if "positions" in data and isinstance(data["positions"], list):
            open_positions = data["positions"]
        elif isinstance(data, list):
            open_positions = data

        active_pos = [p for p in open_positions if float(p.get("size", 0) or 0) > 0]

        if not active_pos:
            return {"message": "No open positions to close"}

        closed = []
        for p in active_pos:
            size = float(p.get("size", 0) or p.get("position", 0))
            symbol = p.get("symbol") or p.get("instrument") or ticker
            side = "sell" if str(p.get("side", "")).lower() == "long" or size > 0 else "buy"
            response = execute_order(side.upper(), symbol, abs(size))
            closed.append({"symbol": symbol, "size": size, "side": side, "response": response})

        return {"message": "Emergency close executed", "closed_positions": closed}
    except Exception as e:
        log_error("api", f"Emergency close failed: {str(e)}", "")
        return {"error": str(e)}


@app.get("/balance")
def balance():
    """Obtiene el balance de Kraken Futures (paper o live según configuración)."""
    try:
        mode = os.getenv("MODE", "paper").lower()
        command = ["kraken", "futures", f"{mode}", "balance", "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON from Kraken CLI: {str(e)}", "raw_output": result.stdout[:500]}
        else:
            return {"error": f"Kraken CLI error (code {result.returncode}): {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Kraken CLI timeout"}
    except FileNotFoundError:
        mode = os.getenv("MODE", "paper").lower()
        if mode == "paper":
            return {
                "portfolio_value": 10000.00,
                "unrealized_pnl": 0.00,
                "available_margin": 10000.00
            }
        return {"error": "Kraken CLI not found. Please install Kraken CLI and add it to PATH."}
    except Exception as e:
        return {"error": str(e)}


@app.get("/position")
def position():
    """Obtiene la posición abierta actual (paper o live según configuración)."""
    try:
        mode = os.getenv("MODE", "paper").lower()
        command = ["kraken", "futures", f"{mode}", "positions", "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                # Handle possible structures
                open_positions = []
                if "positions" in data and isinstance(data["positions"], list):
                    open_positions = data["positions"]
                elif isinstance(data, list):
                    open_positions = data

                # Filter out empty/closed positions (usually size = 0)
                active_pos = [p for p in open_positions if float(p.get("size", 0) or 0) > 0]

                if not active_pos:
                    return {"position": None}

                p = active_pos[0]
                return {
                    "position": {
                        "symbol": p.get("symbol") or p.get("instrument") or "UNKNOWN",
                        "side": "long" if str(p.get("side", "")).lower() == "long" or float(p.get("position", p.get("size", 1))) > 0 else "short",
                        "size": float(p.get("size", 0) or p.get("position", 0)),
                        "entry_price": float(p.get("entry_price", 0) or p.get("price", 0)),
                        "current_price": float(p.get("current_price", 0) or p.get("mark_price", 0)),
                        "pnl_usd": float(p.get("unrealized_pnl", 0) or p.get("pnl", 0)),
                        "pnl_pct": float(p.get("unrealized_pnl_pct", 0) or p.get("pnl_pct", 0))
                    }
                }
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON from Kraken CLI: {str(e)}"}
        else:
            return {"error": f"Kraken CLI error (code {result.returncode}): {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Kraken CLI timeout"}
    except FileNotFoundError:
        return {"error": "Kraken CLI not found."}
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
