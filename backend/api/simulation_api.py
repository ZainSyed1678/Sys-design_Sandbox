from flask import Blueprint, request, jsonify
from core.simulation_manager import sim_manager

simulation_bp = Blueprint('simulation', __name__)

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    data = request.json
    if not data or 'nodes' not in data:
        return jsonify({"status": "error", "message": "No JSON graph given"}), 400
        
    sim_id = sim_manager.create_simulation(data)
    sim = sim_manager.get_simulation(sim_id)
    
    if not sim or sim.state.value == "FAILED":
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
