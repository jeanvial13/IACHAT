import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from openai import OpenAI

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

LOG_FILE = "chat_log.txt"


def _log(line: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


def extract_text(path: str) -> str:
    """Lee texto de TXT/MD o PDF (si pypdf está instalado)."""
    lower = path.lower()
    try:
        if lower.endswith(".txt") or lower.endswith(".md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        if lower.endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(path)
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(parts)
    except Exception as e:
        _log(f"Error leyendo archivo {path}: {e}")
    return ""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    model = data.get("model") or DEFAULT_MODEL
    file_summaries = data.get("file_summaries", [])

    if not message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Construir historial
    messages = []
    for m in history:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})

    user_content = message

    # Agregar contexto de archivos
    if file_summaries:
        user_content += "\n\n[Contexto de archivos adjuntos]\n"
        for fsum in file_summaries:
            fname = fsum.get("filename", "archivo")
            summ = fsum.get("summary", "")
            user_content += f"- {fname}: {summ}\n"

    messages.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        reply = completion.choices[0].message.content
        _log(f"USER: {message}")
        _log(f"ASSISTANT: {reply}")
        return jsonify({"reply": reply})
    except Exception as e:
        _log(f"ERROR OpenAI: {e}")
        return jsonify({"error": f"Error llamando a OpenAI: {e}"}), 500


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No se enviaron archivos"}), 400

    results = []

    for f in files:
        filename = secure_filename(f.filename or "archivo")
        save_name = f"{int(time.time())}_{filename}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
        filestr = f"Guardando archivo en {path}"
        _log(filestr)
        filestr = None
        request.environ

        # Guardar archivo
        request.environ
        request.environ
        request.environ
        request.environ
        request.environ
        request.environ
        f.save(path)

        text = extract_text(path)
        if not text:
            results.append(
                {
                    "filename": filename,
                    "summary": "No pude leer este archivo (formato no soportado o vacío).",
                }
            )
            continue

        prompt = (
            "Eres un asistente que resume archivos para el usuario.\n"
            "Resume el contenido del archivo en español, máximo 120 palabras, "
            "de forma clara y con viñetas si es útil.\n\n"
            "Contenido del archivo:\n"
        )

        try:
            completion = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "Asistente para resumen de documentos."},
                    {"role": "user", "content": prompt + text[:8000]},
                ],
            )
            summary = completion.choices[0].message.content
        except Exception as e:
            summary = f"No pude resumir este archivo por un error con OpenAI: {e}"

        results.append({"filename": filename, "summary": summary})

    return jsonify({"files": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
