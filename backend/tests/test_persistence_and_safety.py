import json
import pytest
from app import app
from extensions import db
from models.design import Design
from core.simulation_manager import (
    validate_topology,
    SimulationInstance,
    SimulationManager,
    SimState,
    MAX_NODES,
    MAX_EDGES,
    MAX_CONCURRENT_RUNS,
)

@pytest.fixture(autouse=True)
def clean_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()

# -------------------------------------------------------------
# 1. Topology Validation Tests
# -------------------------------------------------------------

def test_topology_validation_valid():
    graph = {
        "nodes": [
            {"id": "c1", "data": {"type": "client"}},
            {"id": "api1", "data": {"type": "api"}},
        ],
        "edges": [
            {"id": "e1", "source": "c1", "target": "api1"},
        ],
    }
    is_valid, err = validate_topology(graph)
    assert is_valid is True
    assert err is None

def test_topology_validation_requires_client():
    graph = {
        "nodes": [
            {"id": "api1", "data": {"type": "api"}},
            {"id": "db1", "data": {"type": "database"}},
        ],
        "edges": [
            {"id": "e1", "source": "api1", "target": "db1"},
        ],
    }
    is_valid, err = validate_topology(graph)
    assert is_valid is False
    assert "at least one Client node" in err

def test_topology_validation_dangling_edge():
    graph = {
        "nodes": [
            {"id": "c1", "data": {"type": "client"}},
        ],
        "edges": [
            {"id": "e1", "source": "c1", "target": "non_existent_server"},
        ],
    }
    is_valid, err = validate_topology(graph)
    assert is_valid is False
    assert "non-existent target node" in err

def test_topology_validation_orphan_nodes():
    graph = {
        "nodes": [
            {"id": "c1", "data": {"type": "client"}},
            {"id": "api1", "data": {"type": "api"}},
            {"id": "db_orphan", "data": {"type": "database"}},
        ],
        "edges": [
            {"id": "e1", "source": "c1", "target": "api1"},
        ],
    }
    is_valid, err = validate_topology(graph)
    assert is_valid is False
    assert "unconnected orphan node(s): db_orphan" in err

# -------------------------------------------------------------
# 2. Design CRUD and Persistence Tests
# -------------------------------------------------------------

def test_design_crud_and_validation():
    client = app.test_client()

    # 1. Validation failure: missing name
    bad_req = {"topology": {"nodes": [], "edges": []}}
    resp = client.post("/api/designs", json=bad_req)
    assert resp.status_code == 400
    assert "name" in resp.get_json()["message"]

    # 2. Create valid design
    design_payload = {
        "name": "E-Commerce Checkout Pipeline",
        "description": "High-availability 3-tier architecture with Redis and PostgreSQL",
        "schema_version": 1,
        "topology": {
            "nodes": [
                {"id": "c1", "data": {"type": "client"}},
                {"id": "api1", "data": {"type": "api"}},
            ],
            "edges": [
                {"id": "e1", "source": "c1", "target": "api1"},
            ],
        },
    }
    resp = client.post("/api/designs", json=design_payload)
    assert resp.status_code == 201
    created = resp.get_json()["design"]
    design_id = created["id"]
    assert created["name"] == "E-Commerce Checkout Pipeline"

    # 3. List designs
    resp = client.get("/api/designs")
    assert resp.status_code == 200
    list_data = resp.get_json()
    assert list_data["count"] == 1
    assert list_data["designs"][0]["id"] == design_id

    # 4. Get design
    resp = client.get(f"/api/designs/{design_id}")
    assert resp.status_code == 200
    assert resp.get_json()["design"]["id"] == design_id

    # 5. Update design
    design_payload["name"] = "Updated Checkout Pipeline"
    resp = client.put(f"/api/designs/{design_id}", json=design_payload)
    assert resp.status_code == 200
    assert resp.get_json()["design"]["name"] == "Updated Checkout Pipeline"

    # 6. Delete design
    resp = client.delete(f"/api/designs/{design_id}")
    assert resp.status_code == 200

    # Verify deleted
    resp = client.get(f"/api/designs/{design_id}")
    assert resp.status_code == 404

# -------------------------------------------------------------
# 3. Design Export, Import, and Share Tests
# -------------------------------------------------------------

def test_design_export_import_share():
    client = app.test_client()

    design_payload = {
        "name": "Social Ingest Pipeline",
        "description": "Kafka consumer fanout",
        "topology": {
            "nodes": [{"id": "c1", "data": {"type": "client"}}],
            "edges": [],
        },
    }
    resp = client.post("/api/designs", json=design_payload)
    design_id = resp.get_json()["design"]["id"]

    # 1. Export design
    exp_resp = client.get(f"/api/designs/{design_id}/export")
    assert exp_resp.status_code == 200
    assert "attachment" in exp_resp.headers["Content-Disposition"]
    exp_data = json.loads(exp_resp.data)
    assert exp_data["name"] == "Social Ingest Pipeline"

    # 2. Import design
    exp_data["name"] = "Imported Social Ingest Pipeline"
    imp_resp = client.post("/api/designs/import", json=exp_data)
    assert imp_resp.status_code == 201
    imp_id = imp_resp.get_json()["design"]["id"]
    assert imp_id != design_id

    # 3. Share design
    share_resp = client.get(f"/api/designs/share/{design_id}")
    assert share_resp.status_code == 200
    sdata = share_resp.get_json()
    assert design_id in sdata["share_url"]

# -------------------------------------------------------------
# 4. Simulation Controls & Lifecycle Tests
# -------------------------------------------------------------

def test_simulation_controls_lifecycle():
    client = app.test_client()

    graph = {
        "nodes": [
            {"id": "c1", "data": {"type": "client", "rate_per_sec": 10.0}},
            {"id": "api1", "data": {"type": "api", "concurrency": 5, "latency": 0.05}},
        ],
        "edges": [
            {"id": "e1", "source": "c1", "target": "api1"},
        ],
    }

    # 1. Start simulation
    resp = client.post("/api/simulation/start", json=graph)
    assert resp.status_code == 200
    sim_id = resp.get_json()["sim_id"]

    # 2. Speed control (set to 5.0x)
    resp = client.post(f"/api/simulation/{sim_id}/speed", json={"speed": 5.0})
    assert resp.status_code == 200
    assert resp.get_json()["speed"] == 5.0

    # 3. Pause simulation
    resp = client.post(f"/api/simulation/{sim_id}/pause")
    assert resp.status_code == 200
    assert resp.get_json()["state"] == "PAUSED"

    # 4. Step simulation (advance 1.0s)
    resp = client.post(f"/api/simulation/{sim_id}/step", json={"seconds": 1.0})
    assert resp.status_code == 200
    assert resp.get_json()["sim_time"] >= 1.0

    # 5. Resume simulation
    resp = client.post(f"/api/simulation/{sim_id}/resume")
    assert resp.status_code == 200
    assert resp.get_json()["state"] == "RUNNING"

    # 6. Stop simulation
    resp = client.post(f"/api/simulation/{sim_id}/stop")
    assert resp.status_code == 200
    assert resp.get_json()["state"] == "STOPPED"

    # 7. Reset simulation
    resp = client.post(f"/api/simulation/{sim_id}/reset")
    assert resp.status_code == 200
    assert resp.get_json()["sim_time"] == 0.0
    assert resp.get_json()["state"] == "CREATED"
