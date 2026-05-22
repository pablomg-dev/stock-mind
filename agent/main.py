import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

from agent.brain import get_decision
from agent.db import init_db, log_decision, log_trade
from agent.executor import MODE, calculate_volume, execute_order, get_balance, get_config
from agent.signals import build_signals

TICKER = os.getenv("TICKER", "PF_NVDAXUSD")
INTERVAL = int(os.getenv("INTERVAL_MINUTES", "15")) * 60


def _float_from(obj: Any, *keys: str) -> float | None:
    """Lee el primer campo presente como float."""
    if not isinstance(obj, dict):
        return None
    for k in keys:
        if k not in obj:
            continue
        try:
            return float(obj[k])
        except (TypeError, ValueError):
            continue
    return None


def _portfolio_usd_from_balance(balance: Any) -> float:
    """Extrae colateral / equity en USD del JSON de Kraken CLI (spot o futures)."""
    default_paper = 1000.0
    if not isinstance(balance, dict):
        return default_paper

    # Spot-style
    usd = balance.get("USD")
    if isinstance(usd, dict):
        v = _float_from(usd, "balance", "available", "equivalent")
        if v is not None:
            return v

    # Futures paper / accounts (nombres habituales en la CLI)
    for key in (
        "equity",
        "portfolioValue",
        "availableMargin",
        "availableBalance",
        "cashBalance",
        "collateralValue",
        "balance",
    ):
        v = _float_from(balance, key)
        if v is not None:
            return v

    result = balance.get("result")
    if isinstance(result, dict):
        inner = _portfolio_usd_from_balance(result)
        if inner != default_paper:
            return inner
        if len(result) == 1:
            only = next(iter(result.values()))
            if isinstance(only, dict):
                inner2 = _portfolio_usd_from_balance(only)
                if inner2 != default_paper:
                    return inner2
        for _k, v in result.items():
            if isinstance(v, dict) and "ZUSD" in v:
                try:
                    return float(v["ZUSD"])
                except (TypeError, ValueError):
                    pass
            if isinstance(v, dict):
                for sub in ("balance", "ebalance", "availableMargin", "equity"):
                    if sub in v:
                        try:
                            return float(v[sub])
                        except (TypeError, ValueError):
                            pass

    accounts = balance.get("accounts")
    if isinstance(accounts, list) and accounts:
        first = accounts[0]
        if isinstance(first, dict):
            inner = _portfolio_usd_from_balance(first)
            if inner != default_paper:
                return inner

    print("[main] No se pudo parsear balance futures; usando valor paper por defecto.")
    return default_paper


def run() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Falta GEMINI_API_KEY: configurá .env o el entorno.")

    init_db()
    print(f"[StockMind] Iniciando en modo {MODE} | Ticker: {TICKER}")

    current_position = 0.0
    entry_price = None  # Precio de entrada para take profit/stop loss
    TAKE_PROFIT_PCT = 0.05  # +5%
    STOP_LOSS_PCT = 0.03  # -3%

    while True:
        try:
            print(f"\n[loop] Calculando señales para {TICKER}...")
            signals = build_signals(TICKER, current_position)
            print(f"[loop] RSI: {signals['rsi']:.1f} | Sentimiento: {signals['sentiment']}")

            decision = get_decision(signals)
            print(f"[loop] Decisión: {decision['action']} | Confianza: {decision['confidence']:.0%}")
            print(f"[loop] Razonamiento: {decision['reasoning']}")

            log_decision(decision, signals)

            # Verificar take profit / stop loss si hay posición abierta
            if current_position > 0 and entry_price is not None:
                current_price = signals["price"]
                price_change_pct = (current_price - entry_price) / entry_price

                if price_change_pct >= TAKE_PROFIT_PCT:
                    print(f"[TAKE PROFIT] Precio subió {price_change_pct:.1%} (+{TAKE_PROFIT_PCT:.0%}). Ejecutando SELL automático...")
                    balance = get_balance()
                    portfolio_value = _portfolio_usd_from_balance(balance)
                    volume = calculate_volume(TICKER, current_price, portfolio_value)
                    response = execute_order("SELL", TICKER, volume)
                    log_trade("SELL", TICKER, volume, current_price, MODE, response)
                    print(f"[TAKE PROFIT] SELL ejecutado: {volume} {TICKER} @ {current_price}")
                    current_position = max(0, current_position - volume)
                    entry_price = None
                    continue
                elif price_change_pct <= -STOP_LOSS_PCT:
                    print(f"[STOP LOSS] Precio bajó {price_change_pct:.1%} (-{STOP_LOSS_PCT:.0%}). Ejecutando SELL automático...")
                    balance = get_balance()
                    portfolio_value = _portfolio_usd_from_balance(balance)
                    volume = calculate_volume(TICKER, current_price, portfolio_value)
                    response = execute_order("SELL", TICKER, volume)
                    log_trade("SELL", TICKER, volume, current_price, MODE, response)
                    print(f"[STOP LOSS] SELL ejecutado: {volume} {TICKER} @ {current_price}")
                    current_position = max(0, current_position - volume)
                    entry_price = None
                    continue

            if decision["action"] in ("BUY", "SELL"):
                balance = get_balance()
                portfolio_value = _portfolio_usd_from_balance(balance)
                volume = calculate_volume(TICKER, signals["price"], portfolio_value)

                response = execute_order(decision["action"], TICKER, volume)
                log_trade(decision["action"], TICKER, volume, signals["price"], MODE, response)
                print(f"[loop] Orden ejecutada: {decision['action']} {volume} {TICKER}")

                if decision["action"] == "BUY":
                    current_position += volume
                    entry_price = signals["price"]
                    print(f"[loop] Precio de entrada guardado: {entry_price}")
                elif decision["action"] == "SELL":
                    current_position = max(0, current_position - volume)
                    if current_position == 0:
                        entry_price = None

        except Exception as e:
            print(f"[loop] Error en ciclo: {e}")

        try:
            interval_sec = get_config().get("interval_minutes", 15) * 60
        except Exception:
            interval_sec = INTERVAL

        print(f"[loop] Próxima ejecución en {interval_sec // 60} minutos...")
        time.sleep(interval_sec)


if __name__ == "__main__":
    run()
