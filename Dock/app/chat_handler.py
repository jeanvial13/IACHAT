from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

chat_bp = Blueprint('chat', __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@chat_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    try:
        completion = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": user_message}],
        )
        reply = completion.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
