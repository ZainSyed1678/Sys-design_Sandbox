from flask import Blueprint, request, jsonify

architecture_bp = Blueprint('architecture', __name__)

@architecture_bp.route('/validate', methods=['POST'])
def validate_architecture():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON rock given"}), 400
    
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    
    if len(nodes) == 0:
        return jsonify({"status": "error", "message": "Canvas is empty!"}), 400
    
    has_client = False
    for n in nodes:
        node_type = n.get('data', {}).get('type')
        if node_type == 'client':
            has_client = True
            
    if not has_client:
        return jsonify({"status": "error", "message": "Need at least one Client box to make requests!"}), 400
        
    return jsonify({"status": "ok", "message": "Architecture looks good to Grog."})
