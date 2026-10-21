import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from api.architecture import architecture_bp
from api.simulation_api import simulation_bp
from api.designs_api import designs_bp
from extensions import socketio, db
from core.simulation_manager import sim_manager
from flask_socketio import join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key')

# 5MB Request size limit (Phase 6)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Database Configuration (PostgreSQL with SQLite fallback)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///designs.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

cors_origin_env = os.environ.get('CORS_ORIGIN', '*')
cors_origins = [o.strip() for o in cors_origin_env.split(',') if o.strip()] if cors_origin_env != '*' else '*'
CORS(app, origins=cors_origins)

db.init_app(app)
socketio.init_app(app, cors_allowed_origins=cors_origins)

# Register Blueprints
app.register_blueprint(architecture_bp, url_prefix='/api/architecture')
app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
app.register_blueprint(designs_bp, url_prefix='/api/designs')

# Create tables within application context
with app.app_context():
    db.create_all()

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "ok",
        "message": "System simulator backend operational",
        "service": "sys-design-simulator-backend",
        "database": "connected"
    })

# -------------------------------------------------------------
# SocketIO Session Isolation & Lifecycle Rooms (Phase 6)
# -------------------------------------------------------------

@socketio.on('join_simulation')
def on_join(data):
    """Client joins an isolated room corresponding to their simulation ID."""
    sim_id = data.get('sim_id')
    if sim_id:
        join_room(sim_id)
        sim_manager.register_client_session(request.sid, sim_id)

@socketio.on('leave_simulation')
def on_leave(data):
    """Client leaves the simulation room."""
    sim_id = data.get('sim_id')
    if sim_id:
        leave_room(sim_id)
        sim_manager.unregister_client_session(request.sid, sim_id)

@socketio.on('disconnect')
def on_disconnect():
    """Client disconnects: automatically cleanup simulations and threads."""
    sim_manager.handle_client_disconnect(request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('BACKEND_PORT', 5000)))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
