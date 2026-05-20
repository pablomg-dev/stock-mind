import json
import os
import subprocess
import requests

MODE = os.getenv("MODE", "paper").lower()
TICKER_DEFAULT = os.getenv("TICKER", "PF_NVDAXUSD")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_config() -> dict:
    """Obtiene configuración dinámica del servidor (leverage, max_position_pct)."""
    try:
        response = requests.get(f"{API_BASE_URL}/config", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                "leverage": data.get("leverage", 5),
                "max_position_pct": data.get("max_position_pct", 10) / 100
            }
    except Exception as e:
        print(f"Error fetching config from API: {e}")
    # Fallback a valores por defecto
    return {
        "leverage": int(os.getenv("FUTURES_LEVERAGE", "5")),
        "max_position_pct": float(os.getenv("MAX_POSITION_PCT", "10")) / 100
    }


def run_kraken(args: list[str]) -> dict:
    """Ejecuta un comando de Kraken CLI y devuelve el resultado como dict."""
    result = subprocess.run(
        ["kraken"] + args + ["-o", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Kraken CLI error: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def get_balance() -> dict:
    """Balance / cuenta futures (paper o live)."""
    if MODE == "paper":
        return run_kraken(["futures", "paper", "balance"])
    return run_kraken(["futures", "accounts"])


def execute_order(action: str, ticker: str, volume: float) -> dict:
    """Ejecuta compra o venta en el perp indicado (paper: futures paper; live: futures order)."""
    verb = action.lower()
    sym = ticker or TICKER_DEFAULT
    config = get_config()
    lev = str(config["leverage"])

    if MODE == "paper":
        return run_kraken(
            [
                "futures",
                "paper",
                verb,
                sym,
                str(volume),
                "--leverage",
                lev,
                "--type",
                "market",
            ]
        )
    # Dead man switch (futures)
    run_kraken(["futures", "cancel-after", "60"])
    return run_kraken(
        [
            "futures",
            "order",
            verb,
            sym,
            str(volume),
            "--leverage",
            lev,
            "--type",
            "market",
        ]
    )


def calculate_volume(ticker: str, price: float, portfolio_value: float, max_pct: float = None) -> float:
    """Calcula el volumen a operar (máximo max_pct del portfolio)."""
    if max_pct is None:
        config = get_config()
        max_pct = config["max_position_pct"]
    max_usd = portfolio_value * max_pct
    volume = max_usd / price
    return round(volume, 4)
