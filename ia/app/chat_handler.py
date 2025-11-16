import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------- Manejo de sesión en memoria -----------

sessions_history = {}
sessions_context = {}


def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def with_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        sid = get_session_id()
        sessions_history.setdefault(sid, [])
        sessions_context.setdefault(sid, [])
        return func(*args, **kwargs, sid=sid)
    return wrapper


# ----------- Cliente OpenAI -----------

def get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está definido en las variables de entorno.")
    return OpenAI(api_key=api_key)


# ----------- Lectura de archivos -----------

def extract_text_from_file(path: str, ext: str) -> str:
    ext = ext.lower()
    if ext == "txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if ext == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    if ext == "docx":
        import docx
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    return ""


def summarize_text(text: str, max_chars: int = 8000) -> str:
    text = text.strip()
    if not text:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars]

    client = get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asistente que resume documentos para usarlos "
                    "como contexto en una conversación. Devuelve un resumen "
                    "claro y conciso en español."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return completion.choices[0].message.content.strip()


# ----------- Rutas -----------

@app.route("/")
@with_session
def index(sid):
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
@with_session
def chat(sid):
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()
    model = data.get("model") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    history = sessions_history[sid]
    context_summaries = sessions_context[sid]

    messages = [
        {
            "role": "system",
            "content": (
                "Eres 'IACHAT ASUSTOR PRO v2', un asistente privado corriendo "
                "en un NAS Asustor. Respondes SIEMPRE en español, de forma clara "
                "y útil. Si el usuario subió archivos, ya tienes resúmenes en el "
                "contexto: úsalos cuando sea relevante."
            ),
        }
    ]

    if context_summaries:
        joined = "\n\n".join(
            f"[Archivo {i+1}]\n{summary}" for i, summary in enumerate(context_summaries)
        )
        messages.append(
            {
                "role": "system",
                "content": (
                    "A continuación tienes resúmenes de archivos cargados por el usuario. "
                    "Úsalos como contexto cuando tenga sentido:\n\n" + joined
                ),
            }
        )

    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = get_client()

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
    )

    assistant_reply = completion.choices[0].message.content.strip()

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})

    return jsonify({"reply": assistant_reply})


@app.route("/upload", methods=["POST"])
@with_session
def upload_file(sid):
    if "files" not in request.files:
        return jsonify({"error": "No se enviaron archivos"}), 400

    uploaded_files = request.files.getlist("files")
    saved = []
    summaries = []

    for f in uploaded_files:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        if not allowed_file(filename):
            saved.append(
                {
                    "name": filename,
                    "status": "unsupported",
                    "message": "Formato no soportado. Solo txt, pdf o docx.",
                }
            )
            continue

        file_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + filename
        path = os.path.join(UPLOAD_FOLDER, file_id)
        f.save(path)

        try:
            text = extract_text_from_file(path, ext)
            if not text.strip():
                saved.append(
                    {
                        "name": filename,
                        "status": "empty",
                        "message": "No pude leer este archivo (texto vacío o no reconocido).",
                    }
                )
                continue

            summary = summarize_text(text)
            if summary:
                sessions_context[sid].append(summary)
                summaries.append(
                    {
                        "name": filename,
                        "summary": summary[:300] + ("..." if len(summary) > 300 else ""),
                    }
                )
                saved.append(
                    {
                        "name": filename,
                        "status": "ok",
                        "message": "Archivo cargado y resumido correctamente.",
                    }
                )
            else:
                saved.append(
                    {
                        "name": filename,
                        "status": "partial",
                        "message": "Se leyó el archivo pero no se pudo generar resumen.",
                    }
                )

        except Exception as e:
            saved.append(
                {
                    "name": filename,
                    "status": "error",
                    "message": f"Error procesando el archivo: {e}",
                }
            )

    return jsonify({"files": saved, "summaries": summaries})


@app.route("/reset", methods=["POST"])
@with_session
def reset_session(sid):
    sessions_history[sid] = []
    sessions_context[sid] = []
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
