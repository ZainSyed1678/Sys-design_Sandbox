import pytest
from simulation.engine import SimulationEngine
from simulation.components import Client, APIServer, Database
from simulation.distributions import Distribution, DistributionType
from simulation.resilience import CircuitBreaker, CircuitState, TokenBucket, RetryPolicy
from simulation.events import Event, EventType

def test_retry_storm_amplifies_load_after_failure():
    """
    Demonstrates that without resilience controls, client retries during a downstream
    outage cause a 'retry storm' that amplifies total request attempts and floods the queue.
    """
    engine = SimulationEngine(seed=42)
    db = Database("db_1", concurrency=2, latency=0.05, max_queue_depth=100)
    api = APIServer("api_1", concurrency=5, latency=0.02, max_queue_depth=50, db_id="db_1", timeout=0.15)
    
    # Aggressive client retries: 3 retries per failure
    retry_policy = RetryPolicy(max_retries=3, base_delay=0.05, backoff_type="fixed", jitter=False)
    client = Client(
        "client_1",
        "api_1",
        rate_per_sec=20.0,
        arrival_dist=Distribution(DistributionType.CONSTANT, mean=1.0 / 20.0),
        timeout=0.15,
        retry_policy=retry_policy,
    )
    
    engine.register_component(db)
    engine.register_component(api)
    engine.register_component(client)

    # Start traffic
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_1"))
    
    # Fail database at t=0.2s
    engine.schedule(Event(time=0.2, type=EventType.COMPONENT_FAILED, target_id="db_1"))
    
    # Recover database at t=0.8s
    engine.schedule(Event(time=0.8, type=EventType.COMPONENT_RECOVERED, target_id="db_1"))
    
    engine.run(until=1.5)

    # Assert measurable load amplification:
    # Total attempts significantly exceed initial client requests
    initial_sent = client.sent
    total_attempts = client.total_attempts
    retries = client.retry_count

    assert retries > 0, "Retries should have occurred during database outage"
    assert total_attempts > initial_sent, "Total attempts must exceed initial requests sent"
    amplification_factor = total_attempts / initial_sent
    assert amplification_factor > 1.5, f"Expected amplification factor > 1.5, got {amplification_factor:.2f}"

def test_circuit_breaker_prevents_system_collapse():
    """
    Demonstrates that a Circuit Breaker on the API server detects downstream failure,
    trips OPEN to fast-fail requests, prevents queue saturation, and recovers to CLOSED
    after the database heals.
    """
    engine = SimulationEngine(seed=42)
    db = Database("db_cb", concurrency=2, latency=0.05, max_queue_depth=50)
    
    # API Server equipped with a Circuit Breaker
    cb = CircuitBreaker(failure_threshold=4, recovery_timeout=0.3, half_open_probes=1, success_threshold=2)
    api = APIServer("api_cb", concurrency=5, latency=0.02, max_queue_depth=50, db_id="db_cb", timeout=0.1, circuit_breaker=cb)
    
    # Client with retries
    retry_policy = RetryPolicy(max_retries=2, base_delay=0.05, backoff_type="fixed", jitter=False)
    client = Client(
        "client_cb",
        "api_cb",
        rate_per_sec=25.0,
        arrival_dist=Distribution(DistributionType.CONSTANT, mean=1.0 / 25.0),
        timeout=0.15,
        retry_policy=retry_policy,
    )

    engine.register_component(db)
    engine.register_component(api)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_cb"))
    
    # Fail DB at t=0.2s
    engine.schedule(Event(time=0.2, type=EventType.COMPONENT_FAILED, target_id="db_cb"))
    # Recover DB at t=1.0s
    engine.schedule(Event(time=1.0, type=EventType.COMPONENT_RECOVERED, target_id="db_cb"))

    engine.run(until=1.6)

    # Circuit breaker must have tripped OPEN during outage
    assert cb.trip_count >= 1, "Circuit breaker should have tripped during outage"
    assert cb.rejected_requests > 0, "Circuit breaker must have rejected requests while OPEN"
    
    # After DB recovery, circuit breaker should transition back to CLOSED
    assert cb.state == CircuitState.CLOSED, f"Circuit breaker should have recovered to CLOSED, currently {cb.state}"

def test_retry_budget_constrains_amplification():
    """
    Demonstrates that an explicit retry budget (e.g. 20% max retries) constrains
    the total number of retries during sustained failure, preventing runaway storms.
    """
    engine = SimulationEngine(seed=42)
    db = Database("db_budget", concurrency=1, latency=0.1, max_queue_depth=20)
    api = APIServer("api_budget", concurrency=2, latency=0.02, max_queue_depth=20, db_id="db_budget", timeout=0.08)

    # Retry policy with a strict 20% retry budget
    budget_ratio = 0.20
    retry_policy = RetryPolicy(max_retries=5, base_delay=0.02, backoff_type="fixed", jitter=False, retry_budget_ratio=budget_ratio)
    
    client = Client(
        "client_budget",
        "api_budget",
        rate_per_sec=30.0,
        arrival_dist=Distribution(DistributionType.CONSTANT, mean=1.0 / 30.0),
        timeout=0.08,
        retry_policy=retry_policy,
    )

    engine.register_component(db)
    engine.register_component(api)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_budget"))
    # Keep DB down for the whole run
    engine.schedule(Event(time=0.1, type=EventType.COMPONENT_FAILED, target_id="db_budget"))

    engine.run(until=1.0)

    # Assert retry budget enforced: retry_attempts <= initial_attempts * budget_ratio + margin
    allowed_max = int(client.sent * budget_ratio) + 2
    assert client.retry_count <= allowed_max, (
        f"Retry count {client.retry_count} exceeded budget allowance {allowed_max} (sent={client.sent})"
    )
    assert retry_policy.budget_exhausted_count > 0, "Budget exhausted counter should be positive"

def test_timeouts_without_retries_drop_without_amplification():
    """
    Demonstrates that timeouts without retries drop slow/degraded requests
    but strictly do NOT amplify load (amplification factor == 1.0).
    """
    engine = SimulationEngine(seed=42)
    db = Database("db_slow", concurrency=2, latency=0.5, max_queue_depth=20)
    api = APIServer("api_slow", concurrency=5, latency=0.05, max_queue_depth=20, db_id="db_slow")

    # Client with timeout=0.1s and max_retries=0
    client = Client(
        "client_no_retry",
        "api_slow",
        rate_per_sec=10.0,
        arrival_dist=Distribution(DistributionType.CONSTANT, mean=0.1),
        timeout=0.10,
        retry_policy=None,  # No retries
    )

    engine.register_component(db)
    engine.register_component(api)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_no_retry"))
    engine.run(until=1.0)

    # Every request should time out because DB latency is 0.5s > 0.1s timeout
    assert client.timeout_count > 0, "Requests should have timed out"
    assert client.retry_count == 0, "No retries should be made"
    # Total attempts must exactly equal requests sent: amplification factor is exactly 1.0
    assert client.total_attempts == client.sent
    assert client.total_attempts / max(1, client.sent) == 1.0

def test_token_bucket_load_shedding():
    """
    Demonstrates Token Bucket rate limiting:
      Bucket capacity = 10, refill rate = 10 tokens/sec.
      Arrival rate = 50 req/sec (5x capacity).
      Requests above capacity are cleanly shed / dropped.
    """
    engine = SimulationEngine(seed=42)
    limiter = TokenBucket(capacity=10.0, refill_rate=10.0)
    server = APIServer("srv_tb", concurrency=20, latency=0.01, rate_limiter=limiter)
    client = Client("cli_tb", "srv_tb", rate_per_sec=50.0)

    engine.register_component(server)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_tb"))
    engine.run(until=1.0)

    # Over 1 second: initial burst 10 + 10 refilled = ~20 accepted, ~30 rejected
    assert limiter.accepted_count > 0
    assert limiter.rejected_count > 0
    assert server.dropped == limiter.rejected_count

def test_partial_degradation_latency_multiplier():
    """
    Demonstrates component degradation:
      Normal latency = 0.05s.
      COMPONENT_DEGRADED event with multiplier=4.0 increases latency to 0.20s.
    """
    engine = SimulationEngine(seed=42)
    server = APIServer("srv_deg", concurrency=5, latency=0.05, max_queue_depth=10)
    engine.register_component(server)

    # Initial state
    assert server.latency_multiplier == 1.0

    # Inject degradation at t=0.1s
    engine.schedule(Event(time=0.1, type=EventType.COMPONENT_DEGRADED, target_id="srv_deg", data={"multiplier": 4.0}))
    # Restore component at t=0.5s
    engine.schedule(Event(time=0.5, type=EventType.COMPONENT_RESTORED, target_id="srv_deg"))

    engine.run(until=0.3)
    assert server.latency_multiplier == 4.0
    assert server.get_state()["degraded"] is True

    engine.run(until=0.6)
    assert server.latency_multiplier == 1.0
    assert server.get_state()["degraded"] is False

def test_network_partition_isolation():
    """
    Demonstrates network partition between two specific nodes:
      Partition between Client and Server_A drops packets between them,
      while Client to Server_B remains healthy and connected.
    """
    engine = SimulationEngine(seed=42)
    srv_a = APIServer("srv_a", concurrency=5, latency=0.05)
    srv_b = APIServer("srv_b", concurrency=5, latency=0.05)
    cli_a = Client("cli_a", "srv_a", rate_per_sec=10.0)
    cli_b = Client("cli_b", "srv_b", rate_per_sec=10.0)

    engine.register_component(srv_a)
    engine.register_component(srv_b)
    engine.register_component(cli_a)
    engine.register_component(cli_b)

    # Partition cli_a <-> srv_a at t=0.2s
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_a"))
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_b"))
    engine.schedule(Event(time=0.2, type=EventType.NETWORK_PARTITION, target_id="engine", data={"source": "cli_a", "target": "srv_a"}))

    engine.run(until=1.0)

    # cli_a requests should have dropped due to partition after t=0.2
    assert cli_a.dropped > 0 or srv_a.dropped > 0
    # cli_b <-> srv_b was never partitioned and should have completed normally
    assert srv_b.completed > 0
    assert srv_b.dropped == 0
