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


def log_trade(action: str, ticker: str, volume: float, price: float, mode: str, response: dict) -> None:
    """Guarda un trade ejecutado."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO trades (timestamp, ticker, action, volume, price, mode, kraken_response)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        ticker,
        action,
        volume,
        price,
        mode,
        json.dumps(response, default=str),
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
