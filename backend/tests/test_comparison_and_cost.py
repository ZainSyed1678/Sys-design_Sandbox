import pytest
from core.cost_model import estimate_architecture_cost, DEFAULT_HOURLY_RATES
from core.comparator import compare_architectures
from core.presets import get_all_presets, get_preset_by_id, SCENARIO_PRESETS
from app import app

def test_cost_model_breakdown():
    """Verify cost calculation across different node types."""
    graph = {
        "nodes": [
            {"id": "c1", "data": {"type": "client"}},
            {"id": "lb1", "data": {"type": "load_balancer"}},
            {"id": "api1", "data": {"type": "api"}},
            {"id": "api2", "data": {"type": "api"}},
            {"id": "cache1", "data": {"type": "cache"}},
            {"id": "db1", "data": {"type": "database"}},
        ]
    }
    cost = estimate_architecture_cost(graph)
    # Expected: client (0) + lb (0.025) + 2*api (2*0.04=0.08) + cache (0.035) + db (0.10) = $0.240 / hr
    expected_hourly = 0.0 + 0.025 + 0.080 + 0.035 + 0.100
    assert abs(cost["total_hourly_cost"] - expected_hourly) < 1e-4
    assert cost["total_monthly_cost"] == round(expected_hourly * 730.0, 2)
    assert "ROUGH_ESTIMATE" in cost["disclaimer"]
    assert cost["breakdown"]["api"]["count"] == 2

def test_compare_architectures():
    """
    Compare Architecture A (single API server) vs Architecture B (two API servers with Load Balancer)
    under the same traffic load and seed.
    """
    arch_a = {
        "nodes": [
            {"id": "client", "data": {"type": "client", "rate_per_sec": 40.0}},
            {"id": "api_single", "data": {"type": "api", "concurrency": 2, "latency": 0.1, "max_queue_depth": 5}},
        ],
        "edges": [
            {"id": "e1", "source": "client", "target": "api_single"},
        ],
    }

    arch_b = {
        "nodes": [
            {"id": "client", "data": {"type": "client", "rate_per_sec": 40.0}},
            {"id": "lb", "data": {"type": "load_balancer", "strategy": "round_robin"}},
            {"id": "api_1", "data": {"type": "api", "concurrency": 2, "latency": 0.1, "max_queue_depth": 5}},
            {"id": "api_2", "data": {"type": "api", "concurrency": 2, "latency": 0.1, "max_queue_depth": 5}},
        ],
        "edges": [
            {"id": "e1", "source": "client", "target": "lb"},
            {"id": "e2", "source": "lb", "target": "api_1"},
            {"id": "e3", "source": "lb", "target": "api_2"},
        ],
    }

    res = compare_architectures(arch_a, arch_b, seed=42, duration=10.0)

    assert "architecture_a" in res
    assert "architecture_b" in res
    assert "comparison_delta" in res
    assert "verdict" in res

    # Architecture B has double capacity, so it should have higher throughput and lower drops
    thp_diff = res["comparison_delta"]["throughput_diff"]
    drop_diff = res["comparison_delta"]["drop_rate_diff"]
    assert thp_diff >= 0, "Architecture B throughput should be >= Architecture A"
    assert drop_diff <= 0, "Architecture B drop rate should be <= Architecture A"

def test_scenario_presets_integrity():
    """Verify that all 4 scenario presets exist and have valid topology, steps, and expected outcomes."""
    expected_keys = ["url_shortener", "social_timeline", "black_friday_spike", "cache_stampede"]
    all_presets = get_all_presets()
    assert len(all_presets) == 4

    for key in expected_keys:
        preset = get_preset_by_id(key)
        assert preset is not None, f"Preset '{key}' missing"
        assert "guided_steps" in preset
        assert len(preset["guided_steps"]) >= 3
        assert "expected_outcome" in preset
        assert "graph" in preset
        assert len(preset["graph"]["nodes"]) >= 3
        assert len(preset["graph"]["edges"]) >= 2

def test_api_endpoints_comparison_presets_and_cost():
    """Test Flask HTTP endpoints for presets, cost estimation, and comparison."""
    client = app.test_client()

    # 1. Presets endpoint
    resp = client.get("/api/simulation/presets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert len(data["presets"]) == 4

    # 2. Specific preset
    resp = client.get("/api/simulation/presets/url_shortener")
    assert resp.status_code == 200
    pdata = resp.get_json()
    assert pdata["preset"]["id"] == "url_shortener"

    # 3. Cost endpoint
    cost_req = {
        "nodes": [
            {"id": "n1", "data": {"type": "load_balancer"}},
            {"id": "n2", "data": {"type": "database"}},
        ]
    }
    resp = client.post("/api/simulation/cost", json=cost_req)
    assert resp.status_code == 200
    cdata = resp.get_json()
    assert cdata["cost"]["total_hourly_cost"] == 0.125  # 0.025 + 0.100

    # 4. Compare endpoint
    comp_req = {
        "architecture_a": SCENARIO_PRESETS["url_shortener"]["graph"],
        "architecture_b": SCENARIO_PRESETS["url_shortener"]["graph"],
        "duration": 5.0,
    }
    resp = client.post("/api/simulation/compare", json=comp_req)
    assert resp.status_code == 200
    cmp_data = resp.get_json()
    assert "comparison" in cmp_data
    assert cmp_data["comparison"]["comparison_delta"]["throughput_diff"] == 0.0
