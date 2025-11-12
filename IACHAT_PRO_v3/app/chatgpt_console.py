from flask import Flask, render_template, request, send_from_directory, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from openai import OpenAI
import os, re, zipfile, glob, json, mimetypes
from datetime import datetime
from chat_handler import chat_bp
from utils.cleanup import cleanup_old_zips
from chat_storage import export_project

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.register_blueprint(chat_bp)

os.makedirs("uploads", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("/data/chats", exist_ok=True)  # volumen persistente

try:
    cleanup_old_zips("downloads", keep_last=100, days=30)
except Exception:
    pass

TEXT_EXTS = {'.txt','.md','.py','.js','.ts','.json','.html','.css','.csv','.xml','.yml','.yaml','.sql','.ini','.cfg','.toml'}

def extract_code_blocks(text: str):
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    files = []
    for lang, code in matches:
        lang = (lang or "txt").strip().lower()
        ext = {
            "python":"py","py":"py","html":"html","css":"css","js":"js","javascript":"js",
            "json":"json","sql":"sql","bash":"sh","shell":"sh","txt":"txt","md":"md","yaml":"yaml","yml":"yml","xml":"xml"
        }.get(lang, "txt")
        fname = f"archivo_{len(files)+1}.{ext}"
        files.append((fname, code.strip()))
    return files

def create_zip_from_response(response_text: str) -> str:
    codes = extract_code_blocks(response_text)
    zip_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_resultado.zip"
    zip_path = os.path.join("downloads", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if codes:
            for fname, content in codes:
                zf.writestr(fname, content)
        else:
            zf.writestr("resultado.txt", response_text)
    return zip_name

def summarize_files_for_prompt(saved_paths):
    lines = []
    total_chars = 0
    MAX_CHARS = 180_000
    for p in saved_paths:
        name = os.path.basename(p)
        ext = os.path.splitext(p)[1].lower()
        size = os.path.getsize(p)
        mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
        if ext in TEXT_EXTS and size <= 250_000:
            try:
                content = open(p, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                content = ""
            if total_chars + len(content) > MAX_CHARS:
                lines.append(f"[[{name}]] ({mime}, {size} bytes) — omitido por tamaño, solo metadatos.")
            else:
                lines.append(f"[[{name}]] ({mime}, {size} bytes) contenido:\n{content}")
                total_chars += len(content)
        else:
            lines.append(f"[[{name}]] ({mime}, {size} bytes) — binario/no texto, solo metadatos.")
    return "\n\n".join(lines)

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/upload")
def upload():
    files = request.files.getlist("file")
    if not files:
        return jsonify({"error":"no_files"}), 400

    saved = []
    for f in files:
        filename = secure_filename(f.filename)
        path = os.path.join("uploads", filename)
        f.save(path)
        saved.append(path)

    summary = summarize_files_for_prompt(saved)
    # La IA generará el ZIP final a partir de los bloques de código que devuelva
    prompt = (
        "Analiza los archivos adjuntos. Si generas código, usa bloques triple backticks con lenguaje, "
        "y separa por archivo (```py, ```html, etc.). Entrega TODO dentro de un ZIP final con nombres adecuados.            \n\n" + summary
    )
    try:
        # Aquí podrías cambiar a responses.create si usas el SDK nuevo con 'responses'
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":prompt}],
        )
        reply = (completion.choices[0].message.content or "").strip()
        zip_name = create_zip_from_response(reply)
        return jsonify({"ok": True, "zip": zip_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/downloads/<path:filename>")
def download(filename):
    return send_from_directory("downloads", filename, as_attachment=True)

@app.get("/list")
def list_zip():
    items = []
    for p in sorted(glob.glob(os.path.join("downloads","*.zip")), key=os.path.getmtime, reverse=True)[:100]:
        items.append({
            "name": os.path.basename(p),
            "mtime": datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"files": items})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
