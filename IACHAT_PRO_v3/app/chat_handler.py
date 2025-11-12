from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Carga la API key desde variable de entorno
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: Falta OPENAI_API_KEY en las variables de entorno.")
client = OpenAI(api_key=api_key)

@app.route("/")
def index():
    return "✅ IACHAT_PRO Backend activo"

@app.route("/chat", methods=["POST"])
def chat():
    """Procesa mensajes enviados desde el frontend"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "⚠️ No se recibió mensaje."})

        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Eres un asistente técnico tipo terminal."},
                {"role": "user", "content": user_message},
            ],
        )

        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ Error interno: {e}"})

# Subida de archivos
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        uploaded_files = request.files.getlist("file")
        if not uploaded_files:
            return jsonify({"error": "No se subió ningún archivo."})

        folder = "uploads"
        os.makedirs(folder, exist_ok=True)
        for file in uploaded_files:
            file.save(os.path.join(folder, file.filename))

        return jsonify({"zip": "Archivos subidos correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
