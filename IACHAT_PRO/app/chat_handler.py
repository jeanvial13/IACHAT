from flask import Blueprint, request, jsonify
from openai import OpenAI
import os, json

chat_bp = Blueprint('chat', __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Precios estimados (USD por 1M tokens) — ajusta si cambian
PRICES = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 5.00, "out": 15.00},
    "gpt-5": {"in": 10.00, "out": 30.00},
}

def add_usage(prompt_t, completion_t):
    # Guarda uso acumulado para estimar costo localmente
    path = "logs/usage.json"
    data = {"prompt_tokens":0, "completion_tokens":0}
    if os.path.exists(path):
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
        except Exception:
            pass
    data["prompt_tokens"] += int(prompt_t or 0)
    data["completion_tokens"] += int(completion_t or 0)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": user_message}],
        )
        msg = completion.choices[0].message
        reply = (msg.content or "").strip()
        usage = getattr(completion, "usage", None)
        if usage:
            add_usage(usage.prompt_tokens, usage.completion_tokens)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/credits', methods=['GET'])
def credits():
    # No hay API pública de billing; calculamos una estimación local con los logs
    path = "logs/usage.json"
    data = {"prompt_tokens":0, "completion_tokens":0}
    if os.path.exists(path):
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
        except Exception:
            pass
    model = MODEL
    prices = PRICES.get(model, PRICES["gpt-4o-mini"])
    cost_in = (data["prompt_tokens"]/1_000_000.0) * prices["in"]
    cost_out = (data["completion_tokens"]/1_000_000.0) * prices["out"]
    est_total = round(cost_in + cost_out, 6)
    return jsonify({
        "model": model,
        "prompt_tokens": data["prompt_tokens"],
        "completion_tokens": data["completion_tokens"],
        "estimated_cost_usd": est_total,
        "note": "Estimación local basada en tokens devueltos por la API. Para crédito real visita platform.openai.com/usage"
    })
