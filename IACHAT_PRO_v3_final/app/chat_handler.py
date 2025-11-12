from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os, openai, traceback

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print('WARNING: OPENAI_API_KEY not set in environment. Set it in Portainer or your env.')
else:
    openai.api_key = openai_api_key

MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        message = (data.get('message') or '').strip()
        project = (data.get('project') or 'default').strip()
        if not message:
            return jsonify({'error': 'Mensaje vacío'}), 400

        # Call OpenAI ChatCompletion
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{'role':'user', 'content': message}],
            max_tokens=1500,
            temperature=0.2
        )
        # compat: some SDKs return choices[0].message.content or choices[0].text
        choice = resp.choices[0]
        reply = ""
        if hasattr(choice, 'message') and isinstance(choice.message, dict):
            reply = choice.message.get('content','')
        else:
            reply = getattr(choice, 'text', '') or str(choice)

        return jsonify({'reply': reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        files = request.files.getlist('file')
        if not files:
            return jsonify({'error':'no_files'}), 400
        os.makedirs('uploads', exist_ok=True)
        saved = []
        for f in files:
            path = os.path.join('uploads', f.filename)
            f.save(path)
            saved.append(path)
        return jsonify({'ok': True, 'saved': len(saved)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/downloads/<path:filename>')
def downloads(filename):
    return send_from_directory('downloads', filename, as_attachment=True)

@app.route('/health')
def health():
    return jsonify({'status':'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
