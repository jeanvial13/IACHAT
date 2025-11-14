import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from openai import OpenAI

app = Flask(__name__, static_folder="static", template_folder="templates")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    msg = data.get("message","")
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":msg}]
        )
        return jsonify({"reply":completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
