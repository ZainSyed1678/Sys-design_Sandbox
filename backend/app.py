from flask import Flask, jsonify
from flask_cors import CORS
import os
from api.architecture import architecture_bp
from api.simulation_api import simulation_bp
from extensions import socketio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'caveman-secret')
CORS(app)

socketio.init_app(app)

app.register_blueprint(architecture_bp, url_prefix='/api/architecture')
app.register_blueprint(simulation_bp, url_prefix='/api/simulation')

@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok", "message": "Grog is awake!"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
