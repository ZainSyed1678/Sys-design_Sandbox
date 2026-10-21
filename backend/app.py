import os
from flask import Flask, jsonify
from flask_cors import CORS
from api.architecture import architecture_bp
from api.simulation_api import simulation_bp
from extensions import socketio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key')

cors_origin_env = os.environ.get('CORS_ORIGIN', '*')
cors_origins = [o.strip() for o in cors_origin_env.split(',') if o.strip()] if cors_origin_env != '*' else '*'
CORS(app, origins=cors_origins)

socketio.init_app(app, cors_allowed_origins=cors_origins)

app.register_blueprint(architecture_bp, url_prefix='/api/architecture')
app.register_blueprint(simulation_bp, url_prefix='/api/simulation')

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "ok",
        "message": "System simulator backend operational",
        "service": "sys-design-simulator-backend"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('BACKEND_PORT', 5000)))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
