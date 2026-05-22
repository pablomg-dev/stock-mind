import json
import os
import re
from typing import TypedDict

import google.generativeai as genai

SYSTEM_PROMPT = """
You are a trading agent specialized in xStocks — tokenized stocks of tech companies
that can be traded 24/7 on Kraken.

Your job is to analyze market signals and make disciplined trading decisions.
You always prioritize capital preservation over maximizing profits.

Trading rules you never violate:
- Never recommend BUY if RSI is over 75 (overbought)
- Never recommend SELL if RSI is under 25 (extreme oversold)
- If confidence is less than 0.5, always return HOLD
- Never recommend a position larger than 15% of the total portfolio
- Always explain your reasoning in English, concisely and specifically (max 3 sentences)

You reply ONLY with valid JSON containing these exact fields:
- action: "BUY", "SELL" or "HOLD"
- ticker: string with the symbol
- confidence: number between 0.0 and 1.0
- reasoning: string with your analysis in English (max 3 sentences)
- risk_note: string with a specific risk to consider in English
"""


class Decision(TypedDict):
    action: str
    ticker: str
    confidence: float
    reasoning: str
    risk_note: str


def get_decision(signals: dict) -> Decision:
    """Llama a Gemini con las señales del mercado y devuelve una decisión de trading."""
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2,
            max_output_tokens=2048,
        ),
        system_instruction=SYSTEM_PROMPT,
    )

    headlines = signals.get("headlines", [])
    headlines_str = ", ".join(str(h) for h in headlines) if headlines else "(sin titulares)"

    prompt = f"""
Analyze the following market signals and make a trading decision:

Ticker: {signals['ticker']}
Current price: ${signals['price']:.2f}
RSI (14): {signals['rsi']:.1f}
MACD: {signals['macd']:.4f} | Signal: {signals['macd_signal']:.4f}
SMA 20: ${signals['sma20']:.2f}
Current position: {signals['current_position']} units
News sentiment: {signals['sentiment']} ({signals['news_count']} articles in 6h)
Recent headlines: {headlines_str}
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
            response = model.generate_content(prompt)
            text = response.text if response.text else "{}"
            m = re.search(r"\{[^{}]*\}", text)
            if m:
                text = m.group(0)
            print("[brain debug]", text)
            text = text.replace("'", '"')
            return json.loads(text)
        except Exception as e:
            if attempt == 1:
                print(f"[brain] Error después de 2 intentos: {e}")
                return fallback

    return fallback
