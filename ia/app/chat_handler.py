import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from openai import OpenAI

# Lectura de PDF y DOCX
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx  # python-docx
except Exception:
    docx = None

app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

LOG_FILE = "chat_log.txt"


def _log(line: str) -> None:
    """Pequeño logger a archivo de texto."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


def extract_text(path: str) -> str:
    """
    Lee texto de varios tipos de archivo:

    - .txt / .md: texto plano
    - .pdf: usando pypdf
    - .docx: usando python-docx

    Para otros tipos, devuelve cadena vacía.
    """
    lower = path.lower()
    try:
        # TXT / MD
        if lower.endswith(".txt") or lower.endswith(".md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # PDF
        if lower.endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(path)
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(parts)

        # DOCX
        if lower.endswith(".docx") and docx is not None:
            document = docx.Document(path)
            paragraphs = [p.text for p in document.paragraphs]
            return "\n".join(paragraphs)

    except Exception as e:
        _log(f"Error leyendo archivo {path}: {e}")

    return ""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat normal: recibe mensaje + historial (del frontend)
    y responde usando el modelo configurado.
    NO se hace nada automático con archivos aquí.
    """
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    model = data.get("model") or DEFAULT_MODEL

    if not message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Construir historial para OpenAI
    messages = []
    for m in history:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

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
    """
    Solo SUBE archivos. NO resume nada.
    Devuelve la lista de archivos subidos con id y nombre interno.

    El resumen solo se hace cuando tú lo pidas desde el chat
    (usando el endpoint /summarize_file).
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No se enviaron archivos"}), 400

    results = []

    for f in files:
        original_name = f.filename or "archivo"
        safe_name = secure_filename(original_name)
        file_id = int(time.time() * 1000)
        stored_name = f"{file_id}_{safe_name}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        f.save(path)

        _log(f"Archivo subido: {original_name} -> {path}")

        results.append(
            {
                "id": file_id,
                "filename": original_name,
                "stored_name": stored_name,
            }
        )

    return jsonify({"files": results})


@app.route("/summarize_file", methods=["POST"])
def summarize_file():
    """
    Resume un archivo concreto (cuando tú lo pides).
    Se llama desde el botón "Resumir" en la UI.
    """
    data = request.get_json() or {}
    stored_name = data.get("stored_name")
    original_name = data.get("filename", stored_name)
    model = data.get("model") or DEFAULT_MODEL

    if not stored_name:
        return jsonify({"error": "stored_name requerido"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    if not os.path.exists(path):
        return jsonify({"error": "Archivo no encontrado en el servidor"}), 404

    text = extract_text(path)
    if not text:
        return jsonify(
            {
                "filename": original_name,
                "summary": "No pude leer este archivo (formato no soportado o vacío).",
            }
        )

    prompt = (
        "Eres un asistente que lee archivos para el usuario.\n"
        "Resume el contenido del archivo en español, máximo 200 palabras, "
        "con buena estructura (viñetas si es útil).\n\n"
        "Contenido del archivo:\n"
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Asistente para análisis y resumen de documentos.",
                },
                {"role": "user", "content": prompt + text[:8000]},
            ],
        )
        summary = completion.choices[0].message.content
    except Exception as e:
        summary = f"No pude resumir este archivo por un error con OpenAI: {e}"

    _log(f"Resumen de archivo {original_name}")
    return jsonify({"filename": original_name, "summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
