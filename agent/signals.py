import json
import os
import re
from typing import Any

import pandas as pd
import requests

try:
    import pandas_ta as ta
except ImportError:
    ta = None

KRAKEN_FUTURES_CHARTS_URL = "https://futures.kraken.com/api/charts/v1/trade"


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


def _run_kraken_json(args: list[str]) -> dict:
    """Ejecuta Kraken CLI y parsea JSON; levanta error descriptivo si falla."""
    import subprocess
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


def get_price(symbol: str) -> float:
    """Último precio vía `kraken futures ticker <symbol> -o json`."""
    data = _run_kraken_json(["futures", "ticker", symbol])
    return _futures_ticker_last(data, symbol)


def get_ohlcv_kraken_futures(symbol: str, resolution: str = "1h") -> pd.DataFrame:
    """Obtiene velas OHLCV reales desde la API pública de Kraken Futures.

    Args:
        symbol: Contrato futures (ej. PF_NVDAXUSD)
        resolution: Intervalo de velas (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)

    Returns:
        DataFrame con columnas: time, open, high, low, close, volume
    """
    url = f"{KRAKEN_FUTURES_CHARTS_URL}/{symbol.upper()}/{resolution}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Error fetching Kraken Futures charts for {symbol}: {e}")

    candles = data.get("candles", [])
    if not candles:
        raise ValueError(f"No candles returned from Kraken Futures API for {symbol} @ {resolution}")

    rows = []
    for c in candles:
        rows.append({
            "time": c.get("time"),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": float(c.get("volume", 0)),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("time", kind="mergesort").reset_index(drop=True)
    # Convertir timestamps de ms a datetime para claridad
    df["datetime"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df


def _calculate_indicators_for_df(df: pd.DataFrame) -> dict:
    """Calcula todos los indicadores técnicos para un DataFrame de velas."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    if n < 30:
        raise ValueError(f"Insuficientes velas para calcular indicadores: {n} (necesita >= 30)")

    # Periodos adaptativos
    rsi_len = min(14, max(2, n - 1))
    sma_len = min(20, max(2, n - 1))
    ema50_len = min(50, max(2, n - 1))
    ema200_len = min(200, max(2, n - 1))
    macd_fast = min(12, max(2, n // 3))
    macd_slow = min(26, max(3, n // 2))
    macd_signal_len = min(9, max(2, macd_slow // 2))
    bb_len = min(20, max(2, n - 1))
    atr_len = min(14, max(2, n - 1))
    stoch_k = min(14, max(2, n - 1))
    stoch_d = min(3, max(2, stoch_k // 3))

    indicators = {}

    if ta:
        # RSI
        rsi_series = ta.rsi(close, length=rsi_len)
        indicators["rsi"] = float(rsi_series.iloc[-1])

        # MACD
        macd_df = ta.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal_len)
        macd_col = f"MACD_{macd_fast}_{macd_slow}_{macd_signal_len}"
        signal_col = f"MACDs_{macd_fast}_{macd_slow}_{macd_signal_len}"
        hist_col = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal_len}"
        indicators["macd"] = float(macd_df[macd_col].iloc[-1])
        indicators["macd_signal"] = float(macd_df[signal_col].iloc[-1])
        indicators["macd_histogram"] = float(macd_df[hist_col].iloc[-1])

        # Medias móviles
        indicators["sma20"] = float(ta.sma(close, length=sma_len).iloc[-1])
        indicators["ema50"] = float(ta.ema(close, length=ema50_len).iloc[-1])
        if n >= 200:
            indicators["ema200"] = float(ta.ema(close, length=ema200_len).iloc[-1])
        else:
            indicators["ema200"] = None

        # Bollinger Bands
        bb_df = ta.bbands(close, length=bb_len, std=2)
        if bb_df is not None:
            # pandas_ta column names vary by version; use positional access as fallback
            bb_cols = list(bb_df.columns)
            indicators["bb_lower"] = float(bb_df.iloc[-1, 0])
            indicators["bb_middle"] = float(bb_df.iloc[-1, 1])
            indicators["bb_upper"] = float(bb_df.iloc[-1, 2])
            indicators["bb_width"] = float((indicators["bb_upper"] - indicators["bb_lower"]) / indicators["bb_middle"])
        else:
            indicators["bb_upper"] = indicators["bb_middle"] = indicators["bb_lower"] = indicators["bb_width"] = None

        # ATR
        atr_series = ta.atr(high, low, close, length=atr_len)
        indicators["atr"] = float(atr_series.iloc[-1])
        indicators["atr_pct"] = float(indicators["atr"] / close.iloc[-1] * 100)

        # Stochastic
        stoch_df = ta.stoch(high, low, close, k=stoch_k, d=stoch_d)
        if stoch_df is not None:
            stoch_cols = list(stoch_df.columns)
            indicators["stoch_k"] = float(stoch_df.iloc[-1, 0])
            indicators["stoch_d"] = float(stoch_df.iloc[-1, 1])
        else:
            indicators["stoch_k"] = indicators["stoch_d"] = None

        # Tendencia EMA
        indicators["trend_ema"] = "bullish" if indicators["ema50"] > indicators["ema200"] else "bearish" if indicators["ema200"] else "neutral"

    else:
        # Fallback manual si pandas_ta no está disponible
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(rsi_len).mean()
        loss = (-delta.clip(upper=0)).rolling(rsi_len).mean()
        rs = gain / loss
        indicators["rsi"] = float((100 - 100 / (1 + rs)).iloc[-1])

        ema_fast = close.ewm(span=macd_fast).mean()
        ema_slow = close.ewm(span=macd_slow).mean()
        macd_line = ema_fast - ema_slow
        indicators["macd"] = float(macd_line.iloc[-1])
        indicators["macd_signal"] = float(macd_line.ewm(span=macd_signal_len).mean().iloc[-1])
        indicators["macd_histogram"] = float(indicators["macd"] - indicators["macd_signal"])

        indicators["sma20"] = float(close.rolling(sma_len).mean().iloc[-1])
        indicators["ema50"] = float(close.ewm(span=ema50_len).mean().iloc[-1])
        indicators["ema200"] = float(close.ewm(span=ema200_len).mean().iloc[-1]) if n >= 200 else None

        # Bollinger Bands manual
        sma = close.rolling(bb_len).mean()
        std = close.rolling(bb_len).std()
        indicators["bb_upper"] = float((sma + 2 * std).iloc[-1])
        indicators["bb_middle"] = float(sma.iloc[-1])
        indicators["bb_lower"] = float((sma - 2 * std).iloc[-1])
        indicators["bb_width"] = float((indicators["bb_upper"] - indicators["bb_lower"]) / indicators["bb_middle"])

        # ATR manual
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators["atr"] = float(tr.rolling(atr_len).mean().iloc[-1])
        indicators["atr_pct"] = float(indicators["atr"] / close.iloc[-1] * 100)

        # Stochastic manual
        lowest_low = low.rolling(stoch_k).min()
        highest_high = high.rolling(stoch_k).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        indicators["stoch_k"] = float(k.iloc[-1])
        indicators["stoch_d"] = float(k.rolling(stoch_d).mean().iloc[-1])

        indicators["trend_ema"] = "bullish" if indicators["ema50"] > indicators["ema200"] else "bearish" if indicators["ema200"] else "neutral"

    # Niveles clave recientes (soporte/resistencia aproximados)
    indicators["recent_high"] = float(high.tail(20).max())
    indicators["recent_low"] = float(low.tail(20).min())
    indicators["price_vs_sma20"] = "above" if close.iloc[-1] > indicators["sma20"] else "below"
    indicators["price_vs_ema50"] = "above" if close.iloc[-1] > indicators["ema50"] else "below"

    return indicators


def calculate_indicators(df: pd.DataFrame) -> dict:
    """Calcula todos los indicadores técnicos para el timeframe principal."""
    return _calculate_indicators_for_df(df)


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

    positive_words = ["surge", "beat", "record", "growth", "bullish", "rally", "strong", "gain", "rise", "rally", "outperform", "upgrade"]
    negative_words = ["crash", "drop", "miss", "layoff", "bearish", "decline", "weak", "fall", "plunge", "sell-off", "downgrade", "loss"]

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

    # Precio actual
    price = get_price(ticker)

    # Velas reales de Kraken Futures - timeframe principal (1H) y mayor (4H)
    df_1h = get_ohlcv_kraken_futures(ticker, resolution="1h")
    df_4h = get_ohlcv_kraken_futures(ticker, resolution="4h")

    # Indicadores para ambos timeframes
    indicators_1h = calculate_indicators(df_1h)
    indicators_4h = calculate_indicators(df_4h)

    # Noticias
    news = get_news_sentiment(ticker_name)

    # Datos de vela actual 1H
    last_candle = df_1h.iloc[-1]

    signals = {
        "ticker": ticker,
        "price": price,
        "current_position": current_position,
        "timeframe": "1h",
        "higher_timeframe": "4h",
        # Indicadores 1H
        "rsi": indicators_1h["rsi"],
        "macd": indicators_1h["macd"],
        "macd_signal": indicators_1h["macd_signal"],
        "macd_histogram": indicators_1h["macd_histogram"],
        "sma20": indicators_1h["sma20"],
        "ema50": indicators_1h["ema50"],
        "ema200": indicators_1h["ema200"],
        "bb_upper": indicators_1h["bb_upper"],
        "bb_middle": indicators_1h["bb_middle"],
        "bb_lower": indicators_1h["bb_lower"],
        "bb_width": indicators_1h["bb_width"],
        "atr": indicators_1h["atr"],
        "atr_pct": indicators_1h["atr_pct"],
        "stoch_k": indicators_1h["stoch_k"],
        "stoch_d": indicators_1h["stoch_d"],
        "trend_ema": indicators_1h["trend_ema"],
        "recent_high": indicators_1h["recent_high"],
        "recent_low": indicators_1h["recent_low"],
        "price_vs_sma20": indicators_1h["price_vs_sma20"],
        "price_vs_ema50": indicators_1h["price_vs_ema50"],
        # Indicadores 4H (tendencia mayor)
        "htf_rsi": indicators_4h["rsi"],
        "htf_macd": indicators_4h["macd"],
        "htf_macd_signal": indicators_4h["macd_signal"],
        "htf_ema50": indicators_4h["ema50"],
        "htf_ema200": indicators_4h["ema200"],
        "htf_trend_ema": indicators_4h["trend_ema"],
        # Noticias
        **news,
        # Metadata de velas
        "candle_open": float(last_candle["open"]),
        "candle_high": float(last_candle["high"]),
        "candle_low": float(last_candle["low"]),
        "candle_close": float(last_candle["close"]),
        "candle_volume": float(last_candle["volume"]),
    }

    return signals
