from flask import Blueprint, request, jsonify
from core.simulation_manager import sim_manager
from core.presets import get_all_presets, get_preset_by_id
from core.cost_model import estimate_architecture_cost
from core.comparator import compare_architectures

simulation_bp = Blueprint('simulation', __name__)

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    data = request.json
    if not data or 'nodes' not in data:
        return jsonify({"status": "error", "message": "No graph data provided"}), 400

    sim_id, err = sim_manager.create_simulation(data)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    sim = sim_manager.get_simulation(sim_id)
    if not sim or sim.state.value == "FAILED":
        return jsonify({"status": "error", "message": "Failed to build topology graph"}), 400

    sim.start()
    return jsonify({"status": "ok", "sim_id": sim_id, "state": sim.state.value})

@simulation_bp.route('/<sim_id>/stop', methods=['POST'])
def stop_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    sim.stop()
    return jsonify({"status": "ok", "state": sim.state.value})

@simulation_bp.route('/<sim_id>/pause', methods=['POST'])
def pause_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    sim.pause()
    return jsonify({"status": "ok", "state": sim.state.value})

@simulation_bp.route('/<sim_id>/resume', methods=['POST'])
def resume_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    sim.resume()
    return jsonify({"status": "ok", "state": sim.state.value})

@simulation_bp.route('/<sim_id>/step', methods=['POST'])
def step_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    data = request.json or {}
    seconds = float(data.get("seconds", 0.5))
    sim.step(seconds=seconds)
    return jsonify({"status": "ok", "state": sim.state.value, "sim_time": round(sim.engine.time, 4)})

@simulation_bp.route('/<sim_id>/reset', methods=['POST'])
def reset_simulation(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    sim.reset()
    return jsonify({"status": "ok", "state": sim.state.value, "sim_time": 0.0})

@simulation_bp.route('/<sim_id>/speed', methods=['POST'])
def set_speed(sim_id):
    sim = sim_manager.get_simulation(sim_id)
    if not sim:
        return jsonify({"status": "error", "message": "Simulation not found"}), 404

    data = request.json or {}
    if "speed" not in data:
        return jsonify({"status": "error", "message": "Field 'speed' is required (0.25 to 100.0)."}), 400

    speed = float(data["speed"])
    sim.set_speed(speed)
    return jsonify({"status": "ok", "speed": sim.speed})

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
        return jsonify({"status": "error", "message": "target_id and event_type are required"}), 400

    success = sim.inject_event(target_id, event_type, event_data)
    if success:
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Invalid event or simulation not running"}), 400

# -------------------------------------------------------------
# Phase 5: Presets, Cost Estimation, and Comparison Endpoints
# -------------------------------------------------------------

@simulation_bp.route('/presets', methods=['GET'])
def list_presets():
    """List all available guided scenario presets."""
    return jsonify({"status": "ok", "presets": get_all_presets()})

@simulation_bp.route('/presets/<preset_id>', methods=['GET'])
def get_preset(preset_id):
    """Retrieve full configuration and guided steps for a preset."""
    preset = get_preset_by_id(preset_id)
    if not preset:
        return jsonify({"status": "error", "message": f"Preset '{preset_id}' not found"}), 404
    return jsonify({"status": "ok", "preset": preset})

@simulation_bp.route('/cost', methods=['POST'])
def estimate_cost():
    """Compute estimated hourly infrastructure cost for an architecture."""
    data = request.json
    if not data or 'nodes' not in data:
        return jsonify({"status": "error", "message": "No graph data provided"}), 400

    custom_rates = data.get("rates")
    cost_info = estimate_architecture_cost(data, custom_rates=custom_rates)
    return jsonify({"status": "ok", "cost": cost_info})

@simulation_bp.route('/compare', methods=['POST'])
def compare():
    """Run two architectures side-by-side under identical seeds and return delta metrics."""
    data = request.json
    if not data or 'architecture_a' not in data or 'architecture_b' not in data:
        return jsonify({"status": "error", "message": "Both architecture_a and architecture_b graphs are required"}), 400

    arch_a = data["architecture_a"]
    arch_b = data["architecture_b"]
    seed = int(data.get("seed", 42))
    duration = float(data.get("duration", 15.0))

    comparison = compare_architectures(arch_a, arch_b, seed=seed, duration=duration)
    return jsonify({"status": "ok", "comparison": comparison})
