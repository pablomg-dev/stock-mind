import json
import os
import re
from typing import TypedDict

import google.generativeai as genai

SYSTEM_PROMPT = """
Sos un agente de trading especializado en xStocks — acciones tokenizadas de empresas tech
que se pueden operar 24/7 en Kraken.

Tu trabajo es analizar señales de mercado y tomar decisiones de trading disciplinadas.
Siempre priorizás la preservación de capital sobre maximizar ganancias.

Reglas de trading que nunca violás:
- Nunca recomendás BUY si el RSI supera 75 (sobrecompra)
- Nunca recomendás SELL si el RSI está por debajo de 25 (sobreventa extrema)
- Si confidence es menor a 0.5, siempre devolvés HOLD
- Nunca recomendás una posición mayor al 15% del portfolio total
- Siempre explicás tu razonamiento en español, conciso y específico (máximo 3 oraciones)

Respondés ÚNICAMENTE con JSON válido con estos campos exactos:
- action: "BUY", "SELL" o "HOLD"
- ticker: string con el símbolo
- confidence: número entre 0.0 y 1.0
- reasoning: string con tu análisis en español (máximo 3 oraciones)
- risk_note: string con un riesgo específico a considerar
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
Analizá las siguientes señales de mercado y tomá una decisión de trading:

Ticker: {signals['ticker']}
Precio actual: ${signals['price']:.2f}
RSI (14): {signals['rsi']:.1f}
MACD: {signals['macd']:.4f} | Signal: {signals['macd_signal']:.4f}
SMA 20: ${signals['sma20']:.2f}
Posición actual: {signals['current_position']} unidades
Sentimiento de noticias: {signals['sentiment']} ({signals['news_count']} artículos en 6h)
Titulares recientes: {headlines_str}
"""

    fallback: Decision = {
        "action": "HOLD",
        "ticker": signals["ticker"],
        "confidence": 0.0,
        "reasoning": "Error al conectar con el modelo. Decisión conservadora por defecto.",
        "risk_note": "Revisar conectividad con Gemini API.",
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
