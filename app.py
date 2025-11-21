
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="public")

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg = data.get("message","")
    return jsonify({"reply": "Demo reply for: " + msg})

@app.route('/')
def home():
    return send_from_directory("public", "index.html")

if __name__ == "__main__":
    app.run()
