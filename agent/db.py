import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("STOCKMIND_DB_PATH", str(_REPO_ROOT / "stockmind.db"))


def init_db() -> None:
    """Crea las tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reasoning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ticker TEXT,
            action TEXT,
            confidence REAL,
            reasoning TEXT,
            risk_note TEXT,
            signals TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ticker TEXT,
            action TEXT,
            volume REAL,
            price REAL,
            mode TEXT,
            kraken_response TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            message TEXT,
            details TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT DEFAULT 'stopped',
            last_heartbeat TEXT,
            last_error TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO agent_status (id, status, last_heartbeat, last_error, updated_at)
        VALUES (1, 'stopped', NULL, NULL, ?)
    """, (datetime.now(timezone.utc).isoformat(),))
    conn.commit()
    # Migración: agregar columna leverage si no existe
    try:
        conn.execute("ALTER TABLE trades ADD COLUMN leverage INTEGER")
    except sqlite3.OperationalError:
        pass  # ya existe
    conn.commit()
    conn.close()


def log_decision(decision: dict, signals: dict) -> None:
    """Guarda la decisión del agente (incluye HOLDs)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO reasoning_log (timestamp, ticker, action, confidence, reasoning, risk_note, signals)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        decision["ticker"],
        decision["action"],
        decision["confidence"],
        decision["reasoning"],
        decision["risk_note"],
        json.dumps(signals, default=str),
    ))
    conn.commit()
    conn.close()


def log_trade(action: str, ticker: str, volume: float, price: float, mode: str, response: dict, leverage: int = 5) -> None:
    """Guarda un trade ejecutado."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO trades (timestamp, ticker, action, volume, price, mode, kraken_response, leverage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        ticker,
        action,
        volume,
        price,
        mode,
        json.dumps(response, default=str),
        leverage,
    ))
    conn.commit()
    conn.close()


def get_recent_decisions(limit: int = 20) -> list[dict]:
    """Devuelve las últimas decisiones para el frontend."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, ticker, action, confidence, reasoning, risk_note
        FROM reasoning_log ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "ticker": r[1], "action": r[2],
         "confidence": r[3], "reasoning": r[4], "risk_note": r[5]}
        for r in rows
    ]


def get_recent_decisions_with_signals(limit: int = 5) -> list[dict]:
    """Devuelve las últimas decisiones incluyendo las señales en formato dict.
    Útil para pasar contexto histórico al modelo de IA.
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, ticker, action, confidence, reasoning, risk_note, signals
        FROM reasoning_log ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    decisions = []
    for r in rows:
        signals = {}
        if r[6]:
            try:
                signals = json.loads(r[6])
            except json.JSONDecodeError:
                pass
        decisions.append({
            "timestamp": r[0],
            "ticker": r[1],
            "action": r[2],
            "confidence": r[3],
            "reasoning": r[4],
            "risk_note": r[5],
            "signals": signals,
        })
    return decisions


def get_recent_trades_only(limit: int = 5) -> list[dict]:
    """Devuelve los últimos trades ejecutados (BUY/SEL reales, no HOLDs)."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, ticker, action, volume, price, mode, leverage
        FROM trades ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "ticker": r[1], "action": r[2],
         "volume": r[3], "price": r[4], "mode": r[5],
         "leverage": r[6], "usd_volume": round(r[3] * r[4], 2)}
        for r in rows
    ]


def get_config_db() -> dict:
    """Obtiene configuración persistente de la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def set_config_db(key: str, value: str) -> None:
    """Guarda o actualiza un valor de configuración."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO config (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (key, value, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def log_error(source: str, message: str, details: str = "") -> None:
    """Guarda un error en el log."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO error_log (timestamp, source, message, details)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        source,
        message,
        details,
    ))
    conn.commit()
    conn.close()


def get_recent_errors(limit: int = 20) -> list[dict]:
    """Devuelve los últimos errores registrados."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, source, message, details
        FROM error_log ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "source": r[1], "message": r[2], "details": r[3]}
        for r in rows
    ]


def update_agent_status(status: str, last_error: str = None) -> None:
    """Actualiza el estado del agente en la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now(timezone.utc).isoformat()
    if status == "running":
        conn.execute("""
            INSERT INTO agent_status (id, status, last_heartbeat, last_error, updated_at)
            VALUES (1, ?, ?, NULL, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                last_heartbeat=excluded.last_heartbeat,
                last_error=NULL,
                updated_at=excluded.updated_at
        """, (status, now, now))
    else:
        conn.execute("""
            INSERT INTO agent_status (id, status, last_heartbeat, last_error, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                last_heartbeat=excluded.last_heartbeat,
                last_error=COALESCE(excluded.last_error, agent_status.last_error),
                updated_at=excluded.updated_at
        """, (status, now, last_error, now))
    conn.commit()
    conn.close()


def get_agent_status() -> dict:
    """Obtiene el estado actual del agente."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT status, last_heartbeat, last_error, updated_at
        FROM agent_status WHERE id = 1
    """).fetchone()
    conn.close()
    if not row:
        return {"status": "unknown", "last_heartbeat": None, "last_error": None, "updated_at": None}
    return {
        "status": row[0],
        "last_heartbeat": row[1],
        "last_error": row[2],
        "updated_at": row[3],
    }


def get_recent_trades(limit: int = 50) -> list[dict]:
    """Devuelve los últimos trades ejecutados."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, ticker, action, volume, price, mode, leverage
        FROM trades ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "ticker": r[1], "action": r[2],
         "volume": r[3], "price": r[4], "mode": r[5],
         "leverage": r[6], "usd_volume": round(r[3] * r[4], 2)}
        for r in rows
    ]
