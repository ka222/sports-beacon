import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows mobile apps to connect safely

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "message": "Sports Beacon API is running"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    # Basic sample authentication check
    if email and password:
        return jsonify({
            "status": "success",
            "message": "Login successful!",
            "user": email
        }), 200
    
    return jsonify({
        "status": "error",
        "message": "Please provide both email and password"
    }), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
