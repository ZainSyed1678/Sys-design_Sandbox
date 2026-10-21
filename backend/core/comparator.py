from typing import Dict, Any, Optional
from simulation.engine import SimulationEngine
from core.simulation_manager import SimulationInstance
from core.cost_model import estimate_architecture_cost
from core.analyzer import analyzer

def compare_architectures(
    arch_a_graph: Dict[str, Any],
    arch_b_graph: Dict[str, Any],
    seed: int = 42,
    duration: float = 15.0,
) -> Dict[str, Any]:
    """
    Executes a side-by-side deterministic simulation of two architectures
    using the identical PRNG seed and duration.
    Computes comparative metrics, latency percentiles, drop rates, costs, and deltas.
    """
    # Clone graphs and ensure identical seeds
    graph_a = dict(arch_a_graph)
    graph_b = dict(arch_b_graph)
    graph_a["seed"] = seed
    graph_b["seed"] = seed

    # 1. Simulate Architecture A
    sim_a = SimulationInstance(sim_id="compare_arch_a", graph=graph_a)
    sim_a.build()
    sim_a.engine.run(until=duration)
    metrics_a = dict(sim_a.engine.metrics)
    states_a = sim_a.engine.get_component_states()
    analysis_a = analyzer.analyze(states_a, metrics_a)
    cost_a = estimate_architecture_cost(graph_a)

    # 2. Simulate Architecture B
    sim_b = SimulationInstance(sim_id="compare_arch_b", graph=graph_b)
    sim_b.build()
    sim_b.engine.run(until=duration)
    metrics_b = dict(sim_b.engine.metrics)
    states_b = sim_b.engine.get_component_states()
    analysis_b = analyzer.analyze(states_b, metrics_b)
    cost_b = estimate_architecture_cost(graph_b)

    # 3. Compute comparative deltas (B minus A)
    thp_a = metrics_a.get("throughput", 0.0)
    thp_b = metrics_b.get("throughput", 0.0)
    thp_delta = round(thp_b - thp_a, 4)

    p95_a = metrics_a.get("latency_p95", 0.0)
    p95_b = metrics_b.get("latency_p95", 0.0)
    p95_delta = round(p95_b - p95_a, 6)

    p99_a = metrics_a.get("latency_p99", 0.0)
    p99_b = metrics_b.get("latency_p99", 0.0)
    p99_delta = round(p99_b - p99_a, 6)

    drop_a = metrics_a.get("drop_rate", 0.0)
    drop_b = metrics_b.get("drop_rate", 0.0)
    drop_delta = round(drop_b - drop_a, 4)

    cost_hourly_a = cost_a.get("total_hourly_cost", 0.0)
    cost_hourly_b = cost_b.get("total_hourly_cost", 0.0)
    cost_delta = round(cost_hourly_b - cost_hourly_a, 4)

    # Verdict synthesis
    verdict = "Architecture B exhibits comparable performance to Architecture A."
    if drop_b < drop_a:
        verdict = f"Architecture B achieved a lower drop rate ({drop_b*100:.1f}% vs {drop_a*100:.1f}%), significantly improving system availability."
    elif p95_b < p95_a and drop_b <= drop_a:
        verdict = f"Architecture B reduced p95 latency by {abs(p95_delta)*1000:.1f}ms without increasing drop rates."
    elif cost_hourly_b < cost_hourly_a and drop_b <= drop_a:
        verdict = f"Architecture B reduced estimated hourly infrastructure costs by ${abs(cost_delta):.3f}/hr with equivalent reliability."

    return {
        "seed": seed,
        "simulated_duration": duration,
        "architecture_a": {
            "metrics": metrics_a,
            "cost": cost_a,
            "findings_count": len(analysis_a.get("findings", [])),
            "findings": analysis_a.get("findings", []),
        },
        "architecture_b": {
            "metrics": metrics_b,
            "cost": cost_b,
            "findings_count": len(analysis_b.get("findings", [])),
            "findings": analysis_b.get("findings", []),
        },
        "comparison_delta": {
            "throughput_diff": thp_delta,
            "latency_p95_diff": p95_delta,
            "latency_p99_diff": p99_delta,
            "drop_rate_diff": drop_delta,
            "hourly_cost_diff": cost_delta,
        },
        "verdict": verdict,
    }
