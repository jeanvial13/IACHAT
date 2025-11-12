from flask import Flask, request, send_from_directory, render_template_string
from openai import OpenAI, RateLimitError, AuthenticationError
from dotenv import load_dotenv
import os, zipfile, re, time, threading
from datetime import datetime

load_dotenv()
client = OpenAI()

os.makedirs("uploads", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

app = Flask(__name__, static_folder="downloads")

# --- Plantilla HTML (simple y moderna) ---
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>GPT File Processor</title>
  <style>
    body { font-family: Arial; background:#101820; color:#fff; text-align:center; padding:30px; }
    h1 { color:#ff4b4b; }
    form { margin: 40px auto; background:#1d1f24; padding:30px; border-radius:10px; width:400px; }
    input[type=file]{ margin:10px; }
    button{ padding:10px 20px; border:none; background:#ff4b4b; color:white; border-radius:5px; cursor:pointer; }
    a { color:#6cf; text-decoration:none; }
  </style>
</head>
<body>
  <h1>🚀 GPT File Processor</h1>
  <form action="/upload" method="post" enctype="multipart/form-data">
    <p>Adjunta un archivo para procesar con IA:</p>
    <input type="file" name="file" required><br>
    <button type="submit">Procesar</button>
  </form>
  {% if result %}
    <h2>✅ Resultado disponible</h2>
    <a href="/downloads/{{result}}" download>📦 Descargar ZIP generado</a>
  {% endif %}
</body>
</html>
"""

# --- Funciones auxiliares ---
def extract_code_blocks(text):
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    files = []
    for lang, code in matches:
        lang = lang.strip().lower() if lang else "txt"
        ext = {"python":"py","py":"py","html":"html","css":"css","js":"js",
                "json":"json","sql":"sql","bash":"sh","txt":"txt"}.get(lang,"txt")
        fname = f"archivo_{len(files)+1}.{ext}"
        files.append((fname, code.strip()))
    return files

def create_zip(response_text):
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

def process_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":f"Analiza o mejora el siguiente archivo:\n{content}"}],
        )
        text = resp.choices[0].message.content
        return create_zip(text)
    except AuthenticationError:
        print("❌ ERROR: Clave inválida")
    except RateLimitError:
        print("🚫 Sin créditos disponibles")

# --- Rutas Flask ---
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    filename = file.filename
    path = os.path.join("uploads", filename)
    file.save(path)
    zip_file = process_file(path)
    return render_template_string(HTML, result=zip_file)

@app.route("/downloads/<path:filename>")
def download(filename):
    return send_from_directory("downloads", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
