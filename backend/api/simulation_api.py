from flask import Blueprint, request, jsonify
from core.simulation_manager import sim_manager

simulation_bp = Blueprint('simulation', __name__)

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    data = request.json
    if not data or 'nodes' not in data:
        return jsonify({"status": "error", "message": "No JSON rock given"}), 400
        
    sim_id = sim_manager.create_simulation(data)
    sim = sim_manager.get_simulation(sim_id)
    
    if sim.state == "FAILED":
        return jsonify({"status": "error", "message": "Failed to build graph"}), 400
        
    sim.start()
    return jsonify({"status": "ok", "sim_id": sim_id, "state": sim.state.value})

@simulation_bp.route('/<sim_id>/stop', methods=['POST'])
def stop_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404
        
    sim.stop()
    return jsonify({"status": "ok", "state": sim.state.value})

@simulation_bp.route('/<sim_id>/status', methods=['GET'])
def get_status(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404
        
    return jsonify({"status": "ok", "data": sim.get_metrics()})

@simulation_bp.route('/<sim_id>/inject', methods=['POST'])
def inject_chaos(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404
        
    data = request.json
    target_id = data.get("target_id")
    event_type = data.get("event_type")
    event_data = data.get("data", {})
    
    if not target_id or not event_type:
        return jsonify({"status": "error", "message": "Need target_id and event_type"}), 400
        
    success = sim.inject_event(target_id, event_type, event_data)
    if success:
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Bad rock or math not running"}), 400
