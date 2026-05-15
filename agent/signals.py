import json
import os
import re
import subprocess
from typing import Any

import pandas as pd
import requests

try:
    import pandas_ta as ta
except ImportError:
    ta = None


def _run_kraken_json(args: list[str]) -> dict:
    """Ejecuta Kraken CLI y parsea JSON; levanta error descriptivo si falla."""
    result = subprocess.run(
        ["kraken"] + args + ["-o", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Kraken CLI error: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def _futures_ticker_last(data: dict[str, Any], contract: str) -> float:
    """Extrae el último precio del JSON de `kraken futures ticker <symbol> -o json`."""
    want = contract.upper().replace(":", "")

    ticker = data.get("ticker")
    if isinstance(ticker, dict) and "last" in ticker:
        return float(ticker["last"])

    last = data.get("last")
    if isinstance(last, (int, float, str)) and str(last) not in ("", "null"):
        return float(last)

    tickers = data.get("tickers")
    if isinstance(tickers, list):
        for t in tickers:
            if not isinstance(t, dict):
                continue
            sym = str(t.get("symbol", "")).upper().replace(":", "")
            pair = str(t.get("pair", "")).upper().replace(":", "")
            if sym == want or pair == want:
                return float(t["last"])
        if len(tickers) == 1 and isinstance(tickers[0], dict) and "last" in tickers[0]:
            return float(tickers[0]["last"])

    if isinstance(tickers, dict):
        for k, t in tickers.items():
            if str(k).upper().replace(":", "") != want:
                continue
            if isinstance(t, dict) and "last" in t:
                return float(t["last"])

    res = data.get("result")
    if isinstance(res, dict):
        inner = res.get(contract) or res.get(want) or res.get(contract.lower())
        if isinstance(inner, dict) and "last" in inner:
            return float(inner["last"])
        if isinstance(inner, list) and inner and isinstance(inner[0], (int, float, str)):
            return float(inner[0])
        if isinstance(res.get("last"), (int, float, str)):
            return float(res["last"])

    raise ValueError(f"No se pudo interpretar el precio en la respuesta de futures ticker: keys={list(data)[:12]!r}")


def _news_symbol_from_contract(contract: str) -> str:
    """Deriva un nombre para NewsAPI (ej. PF_NVDAXUSD -> NVDA)."""
    override = os.getenv("NEWS_SYMBOL", "").strip()
    if override:
        return override
    s = re.sub(r"^PF_", "", contract, flags=re.I)
    s = re.sub(r"USD$", "", s, flags=re.I)
    if len(s) >= 5 and s.upper().endswith("X"):
        return s[:-1]
    return s or contract


def get_price(symbol: str) -> float:
    """Último precio vía `kraken futures ticker <symbol> -o json`."""
    data = _run_kraken_json(["futures", "ticker", symbol])
    return _futures_ticker_last(data, symbol)


def _futures_history_trades(data: dict[str, Any]) -> list[dict]:
    """Lista de trades desde la respuesta de `kraken futures history <symbol> -o json`."""
    h = data.get("history")
    if isinstance(h, list) and h:
        return [t for t in h if isinstance(t, dict)]

    res = data.get("result")
    if isinstance(res, dict):
        for key in ("history", "trades"):
            inner = res.get(key)
            if isinstance(inner, list) and inner:
                return [t for t in inner if isinstance(t, dict)]
    if isinstance(res, list) and res:
        return [t for t in res if isinstance(t, dict)]

    return []


def get_ohlcv(symbol: str, interval: int = 60) -> pd.DataFrame:
    """Construye un DataFrame de precios desde el historial público de trades (futures).

    Usa `kraken futures history <symbol> -o json` (no `ohlc` spot). Cada fila es un trade:
    open/high/low/close coinciden con el precio del fill; `interval` se conserva en la firma
    por compatibilidad (la API suele devolver un máximo de ~100 trades).
    """
    _ = interval
    data = _run_kraken_json(["futures", "history", symbol])
    trades = _futures_history_trades(data)
    if not trades:
        raise ValueError(
            f"Sin trades en futures history para {symbol!r}. Claves top-level: {list(data)[:20]!r}"
        )

    rows: list[dict[str, Any]] = []
    for t in trades:
        if not isinstance(t, dict) or t.get("price") is None:
            continue
        ts = t.get("time") or t.get("timestamp")
        if not ts:
            continue
        try:
            px = float(t["price"])
        except (TypeError, ValueError):
            continue
        sz = t.get("size", t.get("qty", 0))
        try:
            sz_f = float(sz) if sz is not None else 0.0
        except (TypeError, ValueError):
            sz_f = 0.0
        rows.append(
            {
                "time": ts,
                "open": px,
                "high": px,
                "low": px,
                "close": px,
                "vwap": px,
                "volume": sz_f,
                "count": 1,
            }
        )

    if len(rows) < 5:
        raise ValueError(
            f"Muy pocos trades válidos ({len(rows)}) para indicadores en {symbol!r}."
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("time", kind="mergesort").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    return df


def calculate_indicators(df: pd.DataFrame) -> dict:
    """Calcula RSI, MACD y SMA sobre el dataframe de precios."""
    close = df["close"]

    if ta:
        rsi = float(ta.rsi(close, length=14).iloc[-1])
        macd_df = ta.macd(close)
        macd = float(macd_df["MACD_12_26_9"].iloc[-1])
        macd_signal = float(macd_df["MACDs_12_26_9"].iloc[-1])
        sma20 = float(ta.sma(close, length=20).iloc[-1])
    else:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])
        sma20 = float(close.rolling(20).mean().iloc[-1])
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = float((ema12 - ema26).iloc[-1])
        macd_signal = float((ema12 - ema26).ewm(span=9).mean().iloc[-1])

    return {"rsi": rsi, "macd": macd, "macd_signal": macd_signal, "sma20": sma20}


def get_news_sentiment(ticker_name: str) -> dict:
    """Obtiene noticias recientes y evalúa sentimiento básico por keywords."""
    api_key = os.getenv("NEWS_API_KEY", "")
    headlines: list[str] = []
    sentiment = "neutral"

    if api_key:
        try:
            url = (
                f"https://newsapi.org/v2/everything?q={ticker_name}"
                "&language=en&pageSize=5&apiKey=" + api_key
            )
            resp = requests.get(url, timeout=5)
            articles = resp.json().get("articles", [])
            headlines = [a["title"] for a in articles[:5] if a.get("title")]
        except Exception:
            pass

    positive_words = ["surge", "beat", "record", "growth", "bullish", "rally", "strong"]
    negative_words = ["crash", "drop", "miss", "layoff", "bearish", "decline", "weak"]

    text = " ".join(headlines).lower()
    pos = sum(1 for w in positive_words if w in text)
    neg = sum(1 for w in negative_words if w in text)

    if pos > neg:
        sentiment = "positive"
    elif neg > pos:
        sentiment = "negative"

    return {
        "sentiment": sentiment,
        "news_count": len(headlines),
        "headlines": headlines[:3],
    }


def build_signals(ticker: str, current_position: float = 0) -> dict:
    """Construye el dict completo de señales para pasarle a brain.py."""
    ticker_name = _news_symbol_from_contract(ticker)

    price = get_price(ticker)
    df = get_ohlcv(ticker)
    indicators = calculate_indicators(df)
    news = get_news_sentiment(ticker_name)

    return {
        "ticker": ticker,
        "price": price,
        "current_position": current_position,
        **indicators,
        **news,
    }
