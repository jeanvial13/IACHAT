import os
import uuid
import json
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from werkzeug.utils import secure_filename

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = Flask(__name__)

# SECRET KEY FIX
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback-secret")


UPLOAD_FOLDER = "/app/uploads"
CHAT_LOG_FILE = "/app/chat_log.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.json
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "Mensaje vacío"}), 400

        sid = get_session_id()

        completion = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL"),
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": user_message},
            ],
        )

        reply = completion.choices[0].message["content"]

        with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{sid} | USER: {user_message}\n")
            f.write(f"{sid} | IA: {reply}\n\n")

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Archivo inválido"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    return jsonify({"message": "Archivo subido correctamente", "filename": filename})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
