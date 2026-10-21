import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from extensions import db

class Design(db.Model):
    __tablename__ = 'designs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(128), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    schema_version = db.Column(db.Integer, nullable=False, default=1)
    topology = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_topology: bool = True) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_topology:
            data["topology"] = self.topology
        return data

def validate_design_payload(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Validates design payload schema. Returns error message or None if valid."""
    if not data or not isinstance(data, dict):
        return "Request body must be a valid JSON object."

    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return "Field 'name' is required and must be a non-empty string."

    topology = data.get("topology")
    if not topology or not isinstance(topology, dict):
        return "Field 'topology' is required and must be an object containing 'nodes' and 'edges'."

    nodes = topology.get("nodes")
    edges = topology.get("edges")
    if not isinstance(nodes, list):
        return "Topology field 'nodes' must be a list."
    if not isinstance(edges, list):
        return "Topology field 'edges' must be a list."

    schema_version = data.get("schema_version", 1)
    if not isinstance(schema_version, int) or schema_version < 1:
        return "Field 'schema_version' must be an integer >= 1."

    return None
