import json
import os
import re
from typing import TypedDict

from google import genai
from google.genai import types

SYSTEM_PROMPT = """
You are an elite quantitative trading agent specialized in xStocks — tokenized stocks of tech companies
traded 24/7 on Kraken Futures with leverage.

Your mission: maximize risk-adjusted returns while strictly preserving capital.
You operate on a 1H primary timeframe, confirmed by a 4H higher timeframe trend filter.

═══════════════════════════════════════════════════════════════════
TECHNICAL ANALYSIS FRAMEWORK
═══════════════════════════════════════════════════════════════════

1. TREND ANALYSIS (Higher Timeframe 4H FIRST, then 1H):
   - 4H trend is KING. Never fight the 4H trend unless extreme divergence.
   - Bullish 4H: price > EMA50 > EMA200, or EMA50 > EMA200
   - Bearish 4H: price < EMA50 < EMA200, or EMA50 < EMA200

2. MOMENTUM:
   - RSI 14: < 30 oversold, > 70 overbought
   - Stochastic %K/%D: < 20 oversold, > 80 overbought
   - MACD: bullish when MACD > signal and histogram positive

3. VOLATILITY & RANGES:
   - Bollinger Bands: price near lower band = potential bounce, near upper = potential rejection
   - ATR%: current volatility. High ATR% (>5%) = wider stops needed, avoid trading
   - Recent 20-candle high/low: key S/R levels

4. PRICE POSITION:
   - Price vs SMA20 / vs EMA50 for short/medium-term bias

═══════════════════════════════════════════════════════════════════
TRADING RULES — NEVER VIOLATE
═══════════════════════════════════════════════════════════════════

- NEVER BUY if 4H trend is bearish AND RSI > 55
- NEVER SELL if 4H trend is bullish AND RSI < 45
- NEVER BUY if RSI > 75 or Stoch K > 85
- NEVER SELL if RSI < 25 or Stoch K < 15
- If confidence < 0.60, return HOLD
- Position max 15% of portfolio
- Avoid when ATR% > 8% (extreme volatility)
- Price outside BB by >2% → expect mean reversion
- If last 2 decisions were the same action and price moved against, be extra cautious

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

Reply ONLY with valid JSON containing these exact fields:
- action: "BUY", "SELL" or "HOLD"
- ticker: string with the symbol
- confidence: number between 0.0 and 1.0 (0.60+ for trades)
- reasoning: concise analysis in English (max 3 sentences)
- risk_note: specific risk to consider in English (1 sentence)
"""


class Decision(TypedDict):
    action: str
    ticker: str
    confidence: float
    reasoning: str
    risk_note: str


def _format_recent_decisions(decisions: list[dict]) -> str:
    """Formatea las decisiones recientes para incluir en el prompt."""
    if not decisions:
        return "No previous decisions in this session."

    lines = []
    for d in decisions:
        ts = d.get("timestamp", "?")[:19]
        action = d.get("action", "?")
        conf = d.get("confidence", 0)
        reasoning = d.get("reasoning", "")
        signals = d.get("signals", {})
        rsi = signals.get("rsi", "?")
        price = signals.get("price", "?")
        line = f"  [{ts}] {action} (conf: {conf:.0%}) @ {price} | RSI: {rsi} | {reasoning[:60]}"
        lines.append(line)
    return "\n".join(lines)


def _fmt(val, decimals: int = 2) -> str:
    """Formatea un valor o devuelve 'N/A'."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def get_decision(signals: dict, recent_decisions: list[dict] | None = None) -> Decision:
    """Llama a Gemini con las señales del mercado y devuelve una decisión de trading."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    headlines = signals.get("headlines", [])
    headlines_str = "\n  - ".join(str(h) for h in headlines) if headlines else "(no recent headlines)"

    recent_decisions_str = _format_recent_decisions(recent_decisions or [])

    prompt = f"""
Analyze the following market signals and make a trading decision.

──────────────────────────────────────────────────────────────────
CURRENT STATE (1H Primary)
──────────────────────────────────────────────────────────────────
Ticker: {signals['ticker']}
Price: ${_fmt(signals['price'])}
Position: {signals['current_position']} units
Candle: O ${_fmt(signals['candle_open'])} H ${_fmt(signals['candle_high'])} L ${_fmt(signals['candle_low'])} C ${_fmt(signals['candle_close'])} Vol {_fmt(signals['candle_volume'], 2)}

MOMENTUM (1H): RSI {_fmt(signals['rsi'], 1)} | Stoch K {_fmt(signals['stoch_k'], 1)} D {_fmt(signals['stoch_d'], 1)}
MACD {_fmt(signals['macd'], 4)} Signal {_fmt(signals['macd_signal'], 4)} Hist {_fmt(signals['macd_histogram'], 4)}

TREND: SMA20 ${_fmt(signals['sma20'])} EMA50 ${_fmt(signals['ema50'])} EMA200 {_fmt(signals['ema200'])}
Price vs SMA20: {signals['price_vs_sma20']} vs EMA50: {signals['price_vs_ema50']} 1H Trend: {signals['trend_ema']}

VOLATILITY: BB Upper ${_fmt(signals['bb_upper'])} Mid ${_fmt(signals['bb_middle'])} Lower ${_fmt(signals['bb_lower'])}
ATR ${_fmt(signals['atr'])} ({_fmt(signals['atr_pct'], 2)}%)
S/R 20c: High ${_fmt(signals['recent_high'])} Low ${_fmt(signals['recent_low'])}

──────────────────────────────────────────────────────────────────
4H CONFIRMATION
──────────────────────────────────────────────────────────────────
RSI {_fmt(signals['htf_rsi'], 1)} | MACD {_fmt(signals['htf_macd'], 4)} Signal {_fmt(signals['htf_macd_signal'], 4)}
EMA50 {_fmt(signals['htf_ema50'])} EMA200 {_fmt(signals['htf_ema200'])} Trend: {signals['htf_trend_ema']}

──────────────────────────────────────────────────────────────────
NEWS: {signals['sentiment']} ({signals['news_count']} articles)
{headlines_str}

──────────────────────────────────────────────────────────────────
RECENT DECISIONS ({len(recent_decisions or [])})
{recent_decisions_str}

──────────────────────────────────────────────────────────────────
INSTRUCTION: Output ONLY valid JSON with action, ticker, confidence, reasoning, risk_note.
"""

    fallback: Decision = {
        "action": "HOLD",
        "ticker": signals["ticker"],
        "confidence": 0.0,
        "reasoning": "Error connecting to the model. Default conservative decision.",
        "risk_note": "Check connectivity with Gemini API.",
    }

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.15,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )
            text = response.text if response.text else "{}"

            # Attempt to parse as JSON; fall back to extraction
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                else:
                    matches = re.findall(r'\{[\s\S]*?"action"[\s\S]*?\}', text)
                    if matches:
                        text = max(matches, key=len)
                text = text.replace("'", '"')
                parsed = json.loads(text)

            print("[brain debug]", json.dumps(parsed)[:400])

            if all(k in parsed for k in ("action", "ticker", "confidence", "reasoning", "risk_note")):
                return parsed
            else:
                print(f"[brain] JSON incompleto: {list(parsed.keys())}")
                if attempt == 1:
                    return fallback
        except Exception as e:
            print(f"[brain] Error intento {attempt + 1}: {e}")
            if attempt == 1:
                return fallback

    return fallback
