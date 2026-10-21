"""Low-Level Design (LLD) REST Endpoints for Architecture Validation and Code Generation."""

import io
import zipfile
from flask import Blueprint, request, jsonify, send_file
from core.lld_generator import (
    LLDClass,
    LLDRelationship,
    LLDArchitectureValidator,
    LLDSkeletonGenerator,
)

lld_blueprint = Blueprint("lld", __name__)


@lld_blueprint.route("/validate", methods=["POST"])
def validate_lld():
    payload = request.get_json() or {}
    nodes_data = payload.get("nodes", [])
    edges_data = payload.get("edges", [])

    classes = [LLDClass.from_dict(n) for n in nodes_data]
    relationships = [LLDRelationship.from_dict(e) for e in edges_data]

    result = LLDArchitectureValidator.validate(classes, relationships)
    return jsonify(result), (200 if result["valid"] else 422)


@lld_blueprint.route("/generate", methods=["POST"])
def generate_code():
    payload = request.get_json() or {}
    nodes_data = payload.get("nodes", [])
    edges_data = payload.get("edges", [])
    language = str(payload.get("language", "typescript")).lower()

    classes = [LLDClass.from_dict(n) for n in nodes_data]
    relationships = [LLDRelationship.from_dict(e) for e in edges_data]

    if language == "python":
        code = LLDSkeletonGenerator.generate_python(classes, relationships)
    else:
        code = LLDSkeletonGenerator.generate_typescript(classes, relationships)

    bundle = LLDSkeletonGenerator.export_archive(classes, relationships)

    return jsonify({
        "language": language,
        "code": code,
        "bundle": bundle,
    }), 200


@lld_blueprint.route("/export", methods=["POST"])
def export_archive():
    payload = request.get_json() or {}
    nodes_data = payload.get("nodes", [])
    edges_data = payload.get("edges", [])

    classes = [LLDClass.from_dict(n) for n in nodes_data]
    relationships = [LLDRelationship.from_dict(e) for e in edges_data]

    bundle = LLDSkeletonGenerator.export_archive(classes, relationships)

    # In-memory ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, content in bundle.items():
            zf.writestr(fname, content)
    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="lld_architecture_skeletons.zip",
    )
