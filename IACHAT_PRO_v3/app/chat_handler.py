from flask import Blueprint, request, jsonify, send_file
from openai import OpenAI
import os, json, io, zipfile
from chat_storage import save_message, load_project, list_projects, export_project

chat_bp = Blueprint('chat', __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PRICES = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 5.00, "out": 15.00},
    "gpt-5": {"in": 10.00, "out": 30.00},
}

def add_usage(prompt_t, completion_t):
    path = "logs/usage.json"
    os.makedirs("logs", exist_ok=True)
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
    message = (data.get("message") or "").strip()
    project = (data.get("project") or "default").strip()
    if not message:
        return jsonify({"error": "Mensaje vacío"}), 400
    try:
        # guardamos input
        save_message(project, "user", message)

        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content": message}],
        )
        reply = (completion.choices[0].message.content or "").strip()
        save_message(project, "assistant", reply)

        usage = getattr(completion, "usage", None)
        if usage:
            add_usage(usage.prompt_tokens, usage.completion_tokens)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/projects', methods=['GET'])
def projects():
    return jsonify({"projects": list_projects()})

@chat_bp.route('/project/export', methods=['GET'])
def project_export():
    name = (request.args.get("project") or "default").strip()
    data, txt = export_project(name)
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}.json", json.dumps(data, ensure_ascii=False, indent=2))
        z.writestr(f"{name}.txt", txt)
    memory.seek(0)
    return send_file(memory, as_attachment=True, download_name=f"{name}_chat_export.zip")

@chat_bp.route('/credits', methods=['GET'])
def credits():
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
        "note": "Estimación local con tokens de la API. Revisa uso real en platform.openai.com/usage"
    })
