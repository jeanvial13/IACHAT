import os
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from openai import OpenAI
import io
import zipfile

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHAT_DIR = BASE_DIR / "chats"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHAT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = None  # None = allow any extension

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    if ALLOWED_EXTENSIONS is None:
        return True
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def get_project_safe_name(project: str) -> str:
    project = project.strip() or "default"
    safe = secure_filename(project)
    return safe or "default"

def get_project_paths(project: str):
    safe = get_project_safe_name(project)
    project_uploads = UPLOAD_DIR / safe
    project_uploads.mkdir(parents=True, exist_ok=True)
    history_file = CHAT_DIR / f"{safe}.jsonl"
    return safe, project_uploads, history_file

def load_history(history_file: Path, max_messages: int = 30):
    messages = []
    if history_file.exists():
        with history_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-max_messages:]
            for line in lines:
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    return messages

def append_to_history(history_file: Path, role: str, content: str, metadata=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "role": role,
        "content": content,
    }
    if metadata:
        entry["meta"] = metadata
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

@app.route("/")
def index():
    # send list of existing projects for sidebar
    projects = []
    for path in CHAT_DIR.glob("*.jsonl"):
        projects.append(path.stem)
    return render_template("index.html", projects=sorted(projects))

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_message = data.get("message", "").strip()
    project = data.get("project", "default")

    safe_project, project_uploads, history_file = get_project_paths(project)

    history = load_history(history_file)

    system_prompt = (
        "Eres 'Andres Personal IA', asistente privado corriendo dentro de un NAS Asustor. "
        "Debes ayudar al usuario con respuestas claras y estructuradas, en el idioma en el que él hable. "
        "No resumas archivos automáticamente. Solo lee archivos del proyecto cuando el usuario lo pida "
        "explícitamente (por ejemplo usando /leer nombre.pdf). Cuando compartas código usa bloques "
        "de código con triple acento grave (```), indicando el lenguaje."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    file_note = ""
    if user_message.startswith("/lista"):
        files = sorted(p.name for p in project_uploads.iterdir() if p.is_file())
        reply = "Archivos en este proyecto:\n" + ("\n".join(files) if files else "(no hay archivos todavía)")
        append_to_history(history_file, "user", user_message)
        append_to_history(history_file, "assistant", reply, {"command": "lista"})
        return jsonify({"reply": reply, "project": safe_project})

    if user_message.startswith("/leer "):
        filename = user_message[len("/leer "):].strip()
        target = project_uploads / filename
        if not target.exists() or not target.is_file():
            reply = f"No encuentro el archivo '{filename}' en el proyecto '{safe_project}'. Usa /lista para ver lo que hay."
            append_to_history(history_file, "user", user_message)
            append_to_history(history_file, "assistant", reply, {"command": "leer", "status": "not_found"})
            return jsonify({"reply": reply, "project": safe_project})

        try:
            content_bytes = target.read_bytes()
            try:
                file_text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                file_text = content_bytes.decode("latin-1", errors="replace")

            file_note = (
                f"El usuario te pide que leas el archivo '{filename}'. "
                "A continuación está su contenido completo. Úsalo para responder.\n\n"
                f"----- CONTENIDO DE {filename} -----\n{file_text}\n----- FIN DEL ARCHIVO -----"
            )
            user_message_for_model = f"/leer {filename}\n\n{file_note}"
        except Exception as exc:  # noqa: BLE001
            reply = f"Ocurrió un error leyendo el archivo: {exc}"
            append_to_history(history_file, "user", user_message)
            append_to_history(history_file, "assistant", reply, {"command": "leer", "status": "error"})
            return jsonify({"reply": reply, "project": safe_project})
    else:
        user_message_for_model = user_message

    append_to_history(history_file, "user", user_message)

    messages.append({"role": "user", "content": user_message_for_model})

    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        assistant_reply = completion.choices[0].message.content
    except Exception as exc:  # noqa: BLE001
        assistant_reply = f"Error al llamar a la API de OpenAI: {exc}"

    append_to_history(history_file, "assistant", assistant_reply)

    return jsonify({"reply": assistant_reply, "project": safe_project})

@app.route("/upload", methods=["POST"])
def upload_file():
    project = request.form.get("project", "default")
    safe_project, project_uploads, history_file = get_project_paths(project)

    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Tipo de archivo no permitido."}), 400

    filename = secure_filename(file.filename)
    save_path = project_uploads / filename
    file.save(save_path)

    append_to_history(
        history_file,
        "system",
        f"Archivo '{filename}' subido al proyecto '{safe_project}'.",
        {"event": "file_upload", "filename": filename},
    )

    return jsonify({"success": True, "filename": filename, "project": safe_project})

@app.route("/files", methods=["GET"])
def list_files():
    project = request.args.get("project", "default")
    safe_project, project_uploads, _ = get_project_paths(project)

    files = []
    for p in sorted(project_uploads.iterdir()):
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size})
    return jsonify({"project": safe_project, "files": files})

@app.route("/download/<project>/<filename>", methods=["GET"])
def download_file(project, filename):
    safe_project, project_uploads, _ = get_project_paths(project)
    return send_from_directory(
        project_uploads,
        filename,
        as_attachment=True,
    )

@app.route("/download_zip", methods=["GET"])
def download_zip():
    project = request.args.get("project", "default")
    safe_project, project_uploads, history_file = get_project_paths(project)

    mem_file = io.BytesIO()
    with zipfile.ZipFile(mem_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if history_file.exists():
            zf.write(history_file, arcname=f"{safe_project}/history.jsonl")

        for p in project_uploads.rglob("*"):
            if p.is_file():
                arcname = f"{safe_project}/uploads/{p.name}"
                zf.write(p, arcname=arcname)

    mem_file.seek(0)
    filename = f"{safe_project}_export.zip"
    return send_file(
        mem_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
