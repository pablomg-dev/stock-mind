import json
import os
import subprocess

MODE = os.getenv("MODE", "paper").lower()
TICKER_DEFAULT = os.getenv("TICKER", "PF_NVDAXUSD")
FUTURES_LEVERAGE = os.getenv("FUTURES_LEVERAGE", "5").strip() or "5"


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
    lev = FUTURES_LEVERAGE

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


def calculate_volume(ticker: str, price: float, portfolio_value: float, max_pct: float = 0.10) -> float:
    """Calcula el volumen a operar (máximo max_pct del portfolio)."""
    max_usd = portfolio_value * max_pct
    volume = max_usd / price
    return round(volume, 4)
