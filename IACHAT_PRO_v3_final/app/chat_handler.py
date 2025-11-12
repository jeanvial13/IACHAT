from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ IACHAT_PRO_v3 está corriendo correctamente dentro de Docker"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
