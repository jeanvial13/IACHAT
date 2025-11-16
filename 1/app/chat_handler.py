import os
from flask import Flask, request, render_template, session
from openai import OpenAI
from uuid import uuid4

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL","gpt-4o-mini")

@app.route("/", methods=["GET","POST"])
def index():
    if "sid" not in session:
        session["sid"] = str(uuid4())

    reply = ""
    if request.method == "POST":
        msg = request.form.get("msg","")
        if msg.strip():
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user","content":msg}]
            )
            reply = response.choices[0].message["content"]
    return render_template("index.html", reply=reply)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
