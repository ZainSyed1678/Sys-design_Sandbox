from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import os
from api.architecture import architecture_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'caveman-secret')
CORS(app) # Allow Face to talk to Brain

socketio = SocketIO(app, cors_allowed_origins="*")

app.register_blueprint(architecture_bp, url_prefix='/api/architecture')

@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok", "message": "Grog is awake!"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
