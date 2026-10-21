import uuid
import json
from flask import Blueprint, request, jsonify, Response
from extensions import db
from models.design import Design, validate_design_payload

designs_bp = Blueprint('designs', __name__)

@designs_bp.route('', methods=['POST'])
def create_design():
    """Create a new named architecture design."""
    data = request.get_json(silent=True)
    err = validate_design_payload(data)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    design = Design(
        name=data["name"].strip(),
        description=data.get("description", "").strip() if data.get("description") else None,
        schema_version=int(data.get("schema_version", 1)),
        topology=data["topology"],
    )
    db.session.add(design)
    db.session.commit()

    return jsonify({"status": "ok", "design": design.to_dict()}), 201

@designs_bp.route('', methods=['GET'])
def list_designs():
    """List all saved architecture designs (summary metadata)."""
    designs = Design.query.order_by(Design.updated_at.desc()).all()
    return jsonify({
        "status": "ok",
        "count": len(designs),
        "designs": [d.to_dict(include_topology=False) for d in designs],
    })

@designs_bp.route('/<design_id>', methods=['GET'])
def get_design(design_id):
    """Retrieve full design including topology by ID."""
    design = db.session.get(Design, design_id)
    if not design:
        return jsonify({"status": "error", "message": f"Design '{design_id}' not found."}), 404
    return jsonify({"status": "ok", "design": design.to_dict()})

@designs_bp.route('/<design_id>', methods=['PUT'])
def update_design(design_id):
    """Update an existing design."""
    design = db.session.get(Design, design_id)
    if not design:
        return jsonify({"status": "error", "message": f"Design '{design_id}' not found."}), 404

    data = request.get_json(silent=True)
    err = validate_design_payload(data)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    design.name = data["name"].strip()
    design.description = data.get("description", "").strip() if data.get("description") else None
    design.schema_version = int(data.get("schema_version", design.schema_version))
    design.topology = data["topology"]
    db.session.commit()

    return jsonify({"status": "ok", "design": design.to_dict()})

@designs_bp.route('/<design_id>', methods=['DELETE'])
def delete_design(design_id):
    """Delete a design by ID."""
    design = db.session.get(Design, design_id)
    if not design:
        return jsonify({"status": "error", "message": f"Design '{design_id}' not found."}), 404

    db.session.delete(design)
    db.session.commit()
    return jsonify({"status": "ok", "message": f"Design '{design_id}' deleted successfully."})

@designs_bp.route('/<design_id>/export', methods=['GET'])
def export_design(design_id):
    """Export a design as a downloadable JSON file."""
    design = db.session.get(Design, design_id)
    if not design:
        return jsonify({"status": "error", "message": f"Design '{design_id}' not found."}), 404

    payload = json.dumps(design.to_dict(), indent=2)
    filename = f"{design.name.lower().replace(' ', '_')}_{design.id[:8]}.json"

    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@designs_bp.route('/import', methods=['POST'])
def import_design():
    """Import a design from JSON payload or file."""
    data = None
    if 'file' in request.files:
        try:
            data = json.load(request.files['file'])
        except Exception as e:
            return jsonify({"status": "error", "message": f"Invalid JSON file: {str(e)}"}), 400
    else:
        data = request.get_json(silent=True)

    err = validate_design_payload(data)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    design = Design(
        name=data["name"].strip(),
        description=data.get("description", "").strip() if data.get("description") else None,
        schema_version=int(data.get("schema_version", 1)),
        topology=data["topology"],
    )
    db.session.add(design)
    db.session.commit()

    return jsonify({"status": "ok", "design": design.to_dict()}), 201

@designs_bp.route('/share/<design_id>', methods=['GET'])
def share_design(design_id):
    """Generate a shareable payload with metadata and direct share link."""
    design = db.session.get(Design, design_id)
    if not design:
        return jsonify({"status": "error", "message": f"Design '{design_id}' not found."}), 404

    base_url = request.host_url.rstrip('/')
    share_url = f"{base_url}/?design_id={design.id}"

    return jsonify({
        "status": "ok",
        "design_id": design.id,
        "share_url": share_url,
        "design": design.to_dict(),
    })
