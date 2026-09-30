import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Sports Beacon API active"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if email and password:
        return jsonify({"status": "success", "message": f"Welcome back, {email}!"}), 200
    return jsonify({"status": "error", "message": "Invalid request"}), 400

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if email and password:
        return jsonify({"status": "success", "message": "Account created successfully!"}), 200
    return jsonify({"status": "error", "message": "Invalid request"}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
