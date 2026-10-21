import math
import pytest
from simulation.engine import SimulationEngine
from simulation.components import Client, APIServer
from simulation.distributions import Distribution, DistributionType
from simulation.events import Event, EventType

def erlang_c(c: int, r: float) -> float:
    """
    Computes Erlang C probability of queuing:
    C(c, r) = (r^c / (c! * (1 - rho))) / (sum_{k=0}^{c-1} r^k / k! + r^c / (c! * (1 - rho)))
    where rho = r / c < 1.
    """
    rho = r / float(c)
    if rho >= 1.0:
        raise ValueError("Erlang C requires traffic intensity rho < 1")
    sum_terms = sum((r ** k) / math.factorial(k) for k in range(c))
    c_term = (r ** c) / (math.factorial(c) * (1.0 - rho))
    return c_term / (sum_terms + c_term)

def test_mm1_queueing_theory():
    """
    Validates M/M/1 queueing against analytic formulas:
      Theoretical mean time in system: W = 1 / (mu - lambda)
      Theoretical utilization: rho = lambda / mu
    Tolerance Justification:
      With virtual duration T=2000s and lambda=8.0 req/s, ~16,000 requests are sampled.
      Central Limit Theorem standard error is sigma / sqrt(N) ~ 1-2%.
      We assert relative error < 5% on both W and rho.
    """
    lambd = 8.0
    mu = 10.0
    engine = SimulationEngine(seed=42)
    server = APIServer(
        "server_1",
        concurrency=1,
        latency=1.0 / mu,
        service_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / mu),
        max_queue_depth=None,  # Unbounded queue
    )
    client = Client(
        "client_1",
        "server_1",
        rate_per_sec=lambd,
        arrival_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / lambd),
    )
    engine.register_component(server)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_1"))
    engine.run(until=2000.0)

    w_theory = 1.0 / (mu - lambd)  # 0.5000 s
    rho_theory = lambd / mu         # 0.8000

    w_sim = engine.metrics["latency_mean"]
    rho_sim = server.get_utilization()

    rel_err_w = abs(w_sim - w_theory) / w_theory
    rel_err_rho = abs(rho_sim - rho_theory) / rho_theory

    assert rel_err_w < 0.05, f"M/M/1 W relative error {rel_err_w*100:.2f}% exceeds 5% tolerance (W_sim={w_sim}, W_theory={w_theory})"
    assert rel_err_rho < 0.05, f"M/M/1 rho relative error {rel_err_rho*100:.2f}% exceeds 5% tolerance (rho_sim={rho_sim}, rho_theory={rho_theory})"

def test_mmc_erlang_c():
    """
    Validates M/M/c multi-server queueing against the Erlang C formula:
      c = 3 servers, mu = 5.0 req/s per server, lambda = 10.0 req/s total.
      r = lambda / mu = 2.0, rho = r / c = 2/3.
      Theoretical Erlang C: C(3, 2) = 4/9 (~0.4444).
      Theoretical mean queue wait time: W_q = C(c, r) / (c * mu - lambda) = (4/9) / 5 = 4/45 (~0.08889 s).
      Theoretical total response time: W = W_q + 1 / mu = 13/45 (~0.28889 s).
    Tolerance Justification:
      With T=2500s and lambda=10.0, ~25,000 requests are processed.
      Expected relative error is within 5%.
    """
    c = 3
    mu = 5.0
    lambd = 10.0
    engine = SimulationEngine(seed=42)
    server = APIServer(
        "server_mmc",
        concurrency=c,
        latency=1.0 / mu,
        service_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / mu),
        max_queue_depth=None,
    )
    client = Client(
        "client_mmc",
        "server_mmc",
        rate_per_sec=lambd,
        arrival_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / lambd),
    )
    engine.register_component(server)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_mmc"))
    engine.run(until=2500.0)

    r = lambd / mu
    c_prob = erlang_c(c, r)
    wq_theory = c_prob / (c * mu - lambd)
    w_theory = wq_theory + (1.0 / mu)
    rho_theory = r / float(c)

    w_sim = engine.metrics["latency_mean"]
    state = server.get_state()
    wq_sim = state["queue_wait_mean"]
    rho_sim = server.get_utilization()

    rel_err_w = abs(w_sim - w_theory) / w_theory
    rel_err_wq = abs(wq_sim - wq_theory) / wq_theory
    rel_err_rho = abs(rho_sim - rho_theory) / rho_theory

    assert rel_err_w < 0.05, f"M/M/c W relative error {rel_err_w*100:.2f}% exceeds 5% (sim={w_sim}, theory={w_theory})"
    assert rel_err_wq < 0.06, f"M/M/c Wq relative error {rel_err_wq*100:.2f}% exceeds 6% (sim={wq_sim}, theory={wq_theory})"
    assert rel_err_rho < 0.05, f"M/M/c rho relative error {rel_err_rho*100:.2f}% exceeds 5% (sim={rho_sim}, theory={rho_theory})"

def test_littles_law_multiple_configurations():
    """
    Validates Little's Law: L = lambda_eff * W.
    Tested across three distinct topologies:
      1. M/M/1 queue with exponential service
      2. M/M/3 queue with multi-server concurrency
      3. M/D/1 queue with constant (deterministic) service time
    Tolerance Justification:
      Little's Law is a conservation law holding for any stationary queueing system.
      With exact time-integral area accumulation in the engine, relative error is < 2%.
    """
    configs = [
        {"name": "M/M/1", "c": 1, "mu": 10.0, "lambd": 7.0, "dist": DistributionType.EXPONENTIAL},
        {"name": "M/M/3", "c": 3, "mu": 6.0, "lambd": 12.0, "dist": DistributionType.EXPONENTIAL},
        {"name": "M/D/1", "c": 1, "mu": 12.0, "lambd": 8.0, "dist": DistributionType.CONSTANT},
    ]

    for cfg in configs:
        engine = SimulationEngine(seed=123)
        server = APIServer(
            "srv",
            concurrency=cfg["c"],
            latency=1.0 / cfg["mu"],
            service_dist=Distribution(cfg["dist"], mean=1.0 / cfg["mu"]),
            max_queue_depth=None,
        )
        client = Client(
            "cli",
            "srv",
            rate_per_sec=cfg["lambd"],
            arrival_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / cfg["lambd"]),
        )
        engine.register_component(server)
        engine.register_component(client)

        engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli"))
        engine.run(until=1500.0)

        l_sim = server.get_mean_system_occupancy()
        lambda_eff = server.get_throughput()
        w_sim = engine.metrics["latency_mean"]
        l_littles = lambda_eff * w_sim

        rel_err = abs(l_sim - l_littles) / max(1e-9, l_sim)
        assert rel_err < 0.02, f"Little's law violated in {cfg['name']}: L_sim={l_sim}, lambda*W={l_littles}, rel_err={rel_err*100:.2f}%"

def test_overload_bounded_queue():
    """
    Validates overload behavior against M/M/1/K analytic loss model:
      When lambda > mu (system overloaded) with finite total capacity K = concurrency + queue_depth,
      the blocking probability P_b is:
        P_b = ((1 - rho) * rho^K) / (1 - rho^(K+1)), where rho = lambda / mu.
    Tolerance Justification:
      With lambda=20, mu=10, K=5, theoretical P_b = 32/63 ~ 50.7937%.
      With 30,000 arrivals (T=1500s), simulated drop rate converges to within 3% relative error.
    """
    lambd = 20.0
    mu = 10.0
    c = 1
    max_q = 4  # Total capacity K = c + max_q = 5
    K = c + max_q
    rho = lambd / mu

    pb_theory = ((1.0 - rho) * (rho ** K)) / (1.0 - (rho ** (K + 1)))

    engine = SimulationEngine(seed=42)
    server = APIServer(
        "srv_overload",
        concurrency=c,
        latency=1.0 / mu,
        service_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / mu),
        max_queue_depth=max_q,
    )
    client = Client(
        "cli_overload",
        "srv_overload",
        rate_per_sec=lambd,
        arrival_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / lambd),
    )
    engine.register_component(server)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_overload"))
    engine.run(until=1500.0)

    total_arrivals = client.sent
    dropped = server.dropped
    drop_rate_sim = dropped / float(total_arrivals)
    rel_err = abs(drop_rate_sim - pb_theory) / pb_theory

    assert rel_err < 0.03, f"Overload drop rate relative error {rel_err*100:.2f}% exceeds 3% (sim={drop_rate_sim}, theory={pb_theory})"

def test_simulation_determinism():
    """
    Validates seeded PRNG determinism:
      - Running identical topology and seed produces 100% bit-for-bit identical results.
      - Running with a different seed produces different results.
    """
    def run_simulation(seed: int):
        engine = SimulationEngine(seed=seed)
        server = APIServer(
            "srv_det",
            concurrency=2,
            latency=0.1,
            service_dist=Distribution(DistributionType.EXPONENTIAL, mean=0.1),
            max_queue_depth=10,
        )
        client = Client(
            "cli_det",
            "srv_det",
            rate_per_sec=15.0,
            arrival_dist=Distribution(DistributionType.EXPONENTIAL, mean=1.0 / 15.0),
        )
        engine.register_component(server)
        engine.register_component(client)
        engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_det"))
        engine.run(until=100.0)
        return (
            dict(engine.metrics),
            list(engine.completed_latencies),
            server.get_state(),
        )

    metrics_a1, latencies_a1, state_a1 = run_simulation(seed=42)
    metrics_a2, latencies_a2, state_a2 = run_simulation(seed=42)
    metrics_b, latencies_b, state_b = run_simulation(seed=999)

    # Identical seeds must match completely
    assert metrics_a1 == metrics_a2
    assert latencies_a1 == latencies_a2
    assert state_a1 == state_a2

    # Different seeds must produce different results
    assert latencies_a1 != latencies_b
    assert metrics_a1["throughput"] != metrics_b["throughput"] or metrics_a1["latency_mean"] != metrics_b["latency_mean"]
