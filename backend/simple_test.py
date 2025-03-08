from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "status": "API is running",
        "message": "This is a test server"
    })

if __name__ == '__main__':
    print("Starting test server on port 8080...")
    app.run(host='0.0.0.0', port=8080, debug=True) 