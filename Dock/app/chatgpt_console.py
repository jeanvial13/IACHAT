from flask import Flask, request, send_from_directory, jsonify, render_template_string
from openai import OpenAI, RateLimitError, AuthenticationError
from dotenv import load_dotenv
import os, zipfile, re, glob
from datetime import datetime

# Cargar variables de entorno y cliente OpenAI
load_dotenv()
client = OpenAI()

# Asegurar carpetas
os.makedirs("uploads", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

app = Flask(__name__, static_folder="downloads")

# ------------ HTML UI (Tailwind + Dropzone) ------------
HTML = r"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>GPT File Processor</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <!-- Tailwind CSS (CDN) -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Dropzone (CDN) -->
  <link rel="stylesheet" href="https://unpkg.com/dropzone@6.0.0-beta.2/dist/dropzone.css"/>
  <script src="https://unpkg.com/dropzone@6.0.0-beta.2/dist/dropzone-min.js"></script>
  <style>
    body{background:#0f172a;color:#e2e8f0;}
    .card{background:#111827;border:1px solid #1f2937}
    .accent{color:#f87171}
    .btn{background:#ef4444;color:#fff}
    .btn:hover{background:#dc2626}
  </style>
</head>
<body class="min-h-screen">
  <header class="py-8 text-center">
    <h1 class="text-3xl md:text-4xl font-bold">🚀 GPT File Processor</h1>
    <p class="mt-2 text-slate-300">Arrastra y suelta archivos. Recibe un <span class="accent font-semibold">ZIP</span> con el código generado (.py, .html, .css, .js, …)</p>
  </header>

  <main class="max-w-5xl mx-auto px-4">
    <!-- Upload Card -->
    <div class="card rounded-2xl p-6 mb-8">
      <h2 class="text-xl font-semibold mb-4">Adjuntar archivo</h2>
      <form action="/upload" class="dropzone" id="gpt-dropzone"></form>

      <div class="mt-4">
        <div id="status" class="text-sm text-slate-400">Listo para subir…</div>
        <div class="w-full bg-slate-800 rounded mt-2 h-2 overflow-hidden">
          <div id="bar" class="h-2 bg-rose-500 w-0 transition-all"></div>
        </div>
      </div>
    </div>

    <!-- Últimos resultados -->
    <div class="card rounded-2xl p-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">Resultados recientes</h2>
        <button id="refresh" class="btn px-3 py-2 rounded-lg text-sm">Actualizar</button>
      </div>
      <ul id="results" class="mt-4 space-y-3"></ul>
    </div>
  </main>

  <footer class="text-center text-xs text-slate-500 py-8">
    Hecho con ❤️ por Jesús & ChatGPT
  </footer>

<script>
  // Configurar Dropzone
  Dropzone.autoDiscover = false;
  const dz = new Dropzone('#gpt-dropzone', {
    url: '/upload',
    maxFilesize: 25, // MB
    timeout: 0,
    parallelUploads: 1,
    createImageThumbnails: false,
    headers: { },
  });

  const statusEl = document.getElementById('status');
  const bar = document.getElementById('bar');

  dz.on('addedfile', () => {
    statusEl.textContent = 'Cargando…';
    bar.style.width = '1%';
  });

  dz.on('uploadprogress', (file, progress) => {
    bar.style.width = progress + '%';
    statusEl.textContent = `Subiendo: ${Math.round(progress)}%`;
  });

  dz.on('success', (file, resp) => {
    bar.style.width = '100%';
    statusEl.textContent = 'Procesando con IA…';
    // resp = {zip: "archivo.zip"}
    if(resp && resp.zip){
      statusEl.textContent = '¡Listo! Descarga disponible abajo.';
      loadResults();
    } else {
      statusEl.textContent = 'Listo, pero no se generó ZIP.';
    }
  });

  dz.on('error', (file, err) => {
    statusEl.textContent = 'Error al subir o procesar el archivo.';
    console.error(err);
  });

  async function loadResults(){
    const ul = document.getElementById('results');
    ul.innerHTML = '<li class="text-slate-400">Cargando…</li>';
    try{
      const r = await fetch('/list');
      const data = await r.json(); // {files:[{name, mtime}]}
      ul.innerHTML = '';
      if(data.files.length === 0){
        ul.innerHTML = '<li class="text-slate-400">Sin resultados todavía.</li>';
        return;
      }
      for(const f of data.files){
        const li = document.createElement('li');
        li.className = 'px-4 py-3 rounded-lg border border-slate-700 flex items-center justify-between';
        li.innerHTML = `
          <div>
            <div class="font-medium">${f.name}</div>
            <div class="text-xs text-slate-400">${f.mtime}</div>
          </div>
          <a class="btn px-3 py-2 rounded-lg text-sm" href="/downloads/${encodeURIComponent(f.name)}" download>Descargar</a>
        `;
        ul.appendChild(li);
      }
    }catch(e){
      ul.innerHTML = '<li class="text-rose-400">No se pudo cargar el listado.</li>';
    }
  }

  document.getElementById('refresh').addEventListener('click', loadResults);
  loadResults();
</script>
</body>
</html>
"""

# ------------ Utilidades ------------
def log_line(text: str):
    log_path = os.path.join("logs", datetime.now().strftime("%Y-%m-%d") + ".txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {text}\n")

def extract_code_blocks(text: str):
    """
    Detecta bloques ```lang ... ``` y devuelve lista de (nombre, contenido)
    """
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
    """
    Crea un ZIP en /downloads. Si hay bloques de código, crea archivos separados;
    si no, guarda un resultado.txt.
    """
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

def process_text_with_gpt(text: str) -> str:
    """
    Llama a OpenAI y devuelve el nombre del ZIP generado.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":"user",
                "content":(
                    "Analiza y mejora el archivo. Si devuelves código, "
                    "entrégalo dentro de bloques triple backticks con lenguaje, "
                    "separando por archivo según corresponda.\n\n"
                    + text
                )
            }],
        )
        out = resp.choices[0].message.content or ""
        log_line("Respuesta tokens recibida.")
        zip_name = create_zip_from_response(out)
        return zip_name
    except AuthenticationError:
        log_line("ERROR: API key inválida.")
        raise
    except RateLimitError:
        log_line("ERROR: Sin créditos.")
        raise

# ------------ Rutas ------------
@app.get("/")
def index():
    return render_template_string(HTML)

@app.post("/upload")
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error":"No file"}), 400
    filename = file.filename
    path = os.path.join("uploads", filename)
    file.save(path)
    log_line(f"Subido: {filename} ({os.path.getsize(path)} bytes)")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        zip_name = process_text_with_gpt(content)
        return jsonify({"ok":True, "zip":zip_name})
    except AuthenticationError:
        return jsonify({"error":"API key inválida / OPENAI_API_KEY ausente"}), 401
    except RateLimitError:
        return jsonify({"error":"Sin créditos disponibles en OpenAI"}), 429
    except Exception as e:
        log_line(f"ERROR: {e}")
        return jsonify({"error":"Error al procesar"}), 500

@app.get("/downloads/<path:filename>")
def download(filename):
    return send_from_directory("downloads", filename, as_attachment=True)

@app.get("/list")
def list_downloads():
    files = []
    for p in sorted(glob.glob(os.path.join("downloads","*.zip")), key=os.path.getmtime, reverse=True)[:30]:
        files.append({
            "name": os.path.basename(p),
            "mtime": datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"files": files})

if __name__ == "__main__":
    # Puerto por defecto 8080 (ajustable con la variable PORT si la deseas)
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
