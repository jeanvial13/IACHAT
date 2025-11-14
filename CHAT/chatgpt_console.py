# chatgpt_console.py
from openai import OpenAI, APIStatusError, AuthenticationError, RateLimitError
from dotenv import load_dotenv
import os, base64, zipfile, re, time
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()
client = OpenAI()

os.makedirs("uploads", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# --- UTILIDADES ---
def save_log(prompt, response):
    log_path = os.path.join("logs", datetime.now().strftime("%Y-%m-%d") + ".txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n🧍‍♂️ Tú: {prompt}\n🤖 ChatGPT: {response}\n{'-'*60}\n")

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ No se pudo leer {path}: {e}")
        return None

def extract_code_blocks(text):
    """
    Detecta bloques de código y sus lenguajes.
    Devuelve una lista de (nombre_sugerido, contenido).
    """
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    files = []

    for lang, code in matches:
        lang = lang.strip().lower() if lang else "txt"
        ext = {
            "python": "py", "py": "py",
            "html": "html", "css": "css",
            "js": "js", "javascript": "js",
            "json": "json", "sql": "sql",
            "bash": "sh", "txt": "txt"
        }.get(lang, "txt")

        filename = f"archivo_{len(files)+1}.{ext}"
        files.append((filename, code.strip()))
    return files

def create_zip_from_code(prompt, response_text):
    """
    Crea archivos según bloques de código detectados en la respuesta.
    Si no hay bloques, guarda todo en resultado.txt
    """
    codes = extract_code_blocks(response_text)
    zip_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_resultado.zip"
    zip_path = os.path.join("downloads", zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if codes:
            for fname, content in codes:
                zipf.writestr(fname, content)
        else:
            zipf.writestr("resultado.txt", response_text)

    print(f"📦 Resultado guardado como ZIP: {zip_path}")
    return zip_path

# --- FUNCIÓN PRINCIPAL DE CHAT ---
def chat_with_gpt(prompt, file_content=None, model="gpt-4o-mini", fallback=False):
    try:
        messages = [{"role": "user", "content": prompt}]
        if file_content:
            messages.append({"role": "user", "content": f"Contenido del archivo:\n{file_content}"})

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        message = completion.choices[0].message
        response = message.content.strip()

        # Guardar logs y archivos
        save_log(prompt, response)
        create_zip_from_code(prompt, response)

    except AuthenticationError:
        print("❌ ERROR: Tu API key es inválida. Configura OPENAI_API_KEY correctamente.")
    except RateLimitError as e:
        if "insufficient_quota" in str(e):
            if fallback:
                print("🚫 Sin créditos disponibles.")
                return
            print("⚠️ Sin créditos en modelo actual. Cambiando a gpt-4o-mini...")
            chat_with_gpt(prompt, file_content, model="gpt-4o-mini", fallback=True)
    except APIStatusError as e:
        print(f"⚠️ Error de API: {e.status_code} - {e.message}")
    except Exception as e:
        print(f"⚠️ Error inesperado: {e}")

# --- MONITOREO AUTOMÁTICO ---
def watch_uploads():
    seen = set(os.listdir("uploads"))
    print("👀 Monitoreando carpeta 'uploads'... coloca tus archivos allí.")
    while True:
        current = set(os.listdir("uploads"))
        new_files = current - seen
        if new_files:
            for file in new_files:
                path = os.path.join("uploads", file)
                print(f"\n📂 Nuevo archivo detectado: {file}")
                content = read_file(path)
                if content:
                    chat_with_gpt(f"Analiza y mejora el archivo {file}.", file_content=content)
            seen = current
        time.sleep(3)

# --- INTERFAZ DE CONSOLA ---
if __name__ == "__main__":
    print("🚀 ChatGPT Console — modo archivos automáticos + ZIP habilitado.\n")
    print("💡 Instrucciones:")
    print("   - Coloca cualquier archivo en la carpeta 'uploads/' para analizarlo.")
    print("   - El resultado se guardará automáticamente en 'downloads/' como ZIP.")
    print("   - Escribe 'salir' para terminar.\n")

    while True:
        user_input = input("💬 Tú (Enter para continuar monitoreando): ").strip()
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("👋 Adiós!")
            break
        if not user_input:
            watch_uploads()
        else:
            chat_with_gpt(user_input)
