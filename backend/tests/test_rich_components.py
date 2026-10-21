import pytest
from simulation.engine import SimulationEngine
from simulation.components import Client, APIServer, Database, Cache
from simulation.load_balancer import LoadBalancingStrategy
from simulation.rich_components import (
    ReadReplicaDatabase,
    ShardedDatabase,
    CDN,
    APIGateway,
    AutoscalingGroup,
)
from simulation.traffic import TrafficProfile, TrafficPatternType
from simulation.cache_model import AdvancedCacheModel
from simulation.events import Event, EventType

# -------------------------------------------------------------
# 1. Load Balancing Strategies Tests
# -------------------------------------------------------------

def test_load_balancer_round_robin():
    """Verify round-robin routes requests sequentially across backends."""
    engine = SimulationEngine(seed=42)
    s1 = APIServer("s1", concurrency=5, latency=0.05)
    s2 = APIServer("s2", concurrency=5, latency=0.05)
    s3 = APIServer("s3", concurrency=5, latency=0.05)
    
    from simulation.components import LoadBalancer
    lb = LoadBalancer("lb", backend_ids=["s1", "s2", "s3"], strategy=LoadBalancingStrategy.ROUND_ROBIN.value)
    
    engine.register_component(s1)
    engine.register_component(s2)
    engine.register_component(s3)
    engine.register_component(lb)

    # Dispatch 9 requests
    for i in range(9):
        engine.schedule(Event(time=float(i) * 0.01, type=EventType.REQUEST_ARRIVED, target_id="lb", data={"request_id": f"r{i}"}))
    
    engine.run(until=1.0)

    # Exactly 3 requests per server
    assert s1.completed == 3
    assert s2.completed == 3
    assert s3.completed == 3

def test_load_balancer_least_connections():
    """Verify least-connections routes to the server with fewer active connections."""
    engine = SimulationEngine(seed=42)
    # s1 is slow (0.5s), s2 is fast (0.01s)
    s1 = APIServer("s1_busy", concurrency=5, latency=0.5)
    s2 = APIServer("s2_idle", concurrency=5, latency=0.01)
    
    from simulation.components import LoadBalancer
    lb = LoadBalancer("lb_lc", backend_ids=["s1_busy", "s2_idle"], strategy=LoadBalancingStrategy.LEAST_CONNECTIONS.value)
    
    engine.register_component(s1)
    engine.register_component(s2)
    engine.register_component(lb)

    # Send 10 rapid requests
    for i in range(10):
        engine.schedule(Event(time=float(i) * 0.005, type=EventType.REQUEST_ARRIVED, target_id="lb_lc", data={"request_id": f"r{i}"}))
    
    engine.run(until=1.0)

    # Fast/idle server must process significantly more requests than slow/busy server
    assert s2.completed > s1.completed

def test_load_balancer_weighted():
    """Verify weighted strategy routes traffic proportionally to weights."""
    engine = SimulationEngine(seed=42)
    s1 = APIServer("s1_light", concurrency=50, latency=0.001)
    s2 = APIServer("s2_heavy", concurrency=50, latency=0.001)
    
    from simulation.components import LoadBalancer
    # s2 has 3x weight of s1
    weights = {"s1_light": 1.0, "s2_heavy": 3.0}
    lb = LoadBalancer("lb_wt", backend_ids=["s1_light", "s2_heavy"], strategy=LoadBalancingStrategy.WEIGHTED.value, weights=weights)
    
    engine.register_component(s1)
    engine.register_component(s2)
    engine.register_component(lb)

    for i in range(400):
        engine.schedule(Event(time=float(i) * 0.001, type=EventType.REQUEST_ARRIVED, target_id="lb_wt", data={"request_id": f"r{i}"}))
    
    engine.run(until=1.0)

    # Expect ratio close to 3:1 (s2 gets ~75%, s1 gets ~25%)
    total = s1.completed + s2.completed
    s2_ratio = s2.completed / total
    assert 0.65 <= s2_ratio <= 0.85, f"Expected weight ratio ~0.75, got {s2_ratio:.2f}"

def test_load_balancer_consistent_hashing():
    """Verify consistent hashing deterministically maps identical keys to the same backend."""
    from simulation.load_balancer import ConsistentHashRing
    ring = ConsistentHashRing(["node_a", "node_b", "node_c"], virtual_nodes=50)

    # Same key always returns the same node
    node_user1 = ring.get_node("user_1001")
    node_user2 = ring.get_node("user_1002")
    node_user3 = ring.get_node("user_1003")

    for _ in range(10):
        assert ring.get_node("user_1001") == node_user1
        assert ring.get_node("user_1002") == node_user2
        assert ring.get_node("user_1003") == node_user3

# -------------------------------------------------------------
# 2. Rich Components Tests
# -------------------------------------------------------------

def test_read_replica_split():
    """Verify ReadReplicaDatabase routes writes to primary and reads to replicas."""
    engine = SimulationEngine(seed=42)
    primary = Database("db_primary", concurrency=5, latency=0.01)
    rep1 = Database("db_rep1", concurrency=5, latency=0.01)
    rep2 = Database("db_rep2", concurrency=5, latency=0.01)
    
    router = ReadReplicaDatabase("db_router", primary_id="db_primary", replica_ids=["db_rep1", "db_rep2"])

    engine.register_component(primary)
    engine.register_component(rep1)
    engine.register_component(rep2)
    engine.register_component(router)

    # 4 writes
    for i in range(4):
        engine.schedule(Event(time=0.01 * i, type=EventType.REQUEST_ARRIVED, target_id="db_router", data={"request_id": f"w{i}", "is_write": True}))
    # 6 reads
    for i in range(6):
        engine.schedule(Event(time=0.05 + 0.01 * i, type=EventType.REQUEST_ARRIVED, target_id="db_router", data={"request_id": f"r{i}", "is_write": False}))

    engine.run(until=0.5)

    assert primary.completed == 4, f"Primary should handle all 4 writes, handled {primary.completed}"
    assert rep1.completed == 3, f"Replica 1 should handle 3 reads, handled {rep1.completed}"
    assert rep2.completed == 3, f"Replica 2 should handle 3 reads, handled {rep2.completed}"

def test_sharded_database_routing():
    """Verify ShardedDatabase deterministically routes requests to shards by key."""
    engine = SimulationEngine(seed=42)
    s0 = Database("shard_0", concurrency=5, latency=0.01)
    s1 = Database("shard_1", concurrency=5, latency=0.01)
    s2 = Database("shard_2", concurrency=5, latency=0.01)
    
    sharded = ShardedDatabase("sharded_db", shard_ids=["shard_0", "shard_1", "shard_2"])

    engine.register_component(s0)
    engine.register_component(s1)
    engine.register_component(s2)
    engine.register_component(sharded)

    # Send requests with diverse shard keys
    for i in range(60):
        engine.schedule(Event(
            time=0.005 * i,
            type=EventType.REQUEST_ARRIVED,
            target_id="sharded_db",
            data={"request_id": f"r{i}", "shard_key": f"tenant_{i}"},
        ))

    engine.run(until=1.0)

    # All shards should receive traffic
    assert s0.completed > 0
    assert s1.completed > 0
    assert s2.completed > 0
    assert s0.completed + s1.completed + s2.completed == 60

def test_cdn_edge_caching():
    """Verify CDN serves hits locally with edge latency and forwards misses to origin."""
    engine = SimulationEngine(seed=42)
    origin = APIServer("origin_api", concurrency=5, latency=0.1)
    cdn = CDN("cdn_edge", origin_id="origin_api", hit_rate=0.8, edge_latency=0.005)

    engine.register_component(origin)
    engine.register_component(cdn)

    for i in range(100):
        engine.schedule(Event(time=0.01 * i, type=EventType.REQUEST_ARRIVED, target_id="cdn_edge", data={"request_id": f"r{i}"}))

    engine.run(until=2.0)

    assert cdn.hits > 0
    assert cdn.misses > 0
    assert origin.completed == cdn.misses

def test_api_gateway_path_routing():
    """Verify API Gateway routes based on URL path prefixes."""
    engine = SimulationEngine(seed=42)
    auth_srv = APIServer("auth_service", concurrency=5, latency=0.01)
    order_srv = APIServer("order_service", concurrency=5, latency=0.01)
    default_srv = APIServer("default_service", concurrency=5, latency=0.01)

    routes = {
        "/api/v1/auth": "auth_service",
        "/api/v1/orders": "order_service",
    }
    gw = APIGateway("gateway", routes=routes, default_target="default_service")

    engine.register_component(auth_srv)
    engine.register_component(order_srv)
    engine.register_component(default_srv)
    engine.register_component(gw)

    engine.schedule(Event(time=0.01, type=EventType.REQUEST_ARRIVED, target_id="gateway", data={"request_id": "r1", "path": "/api/v1/auth/login"}))
    engine.schedule(Event(time=0.02, type=EventType.REQUEST_ARRIVED, target_id="gateway", data={"request_id": "r2", "path": "/api/v1/orders/create"}))
    engine.schedule(Event(time=0.03, type=EventType.REQUEST_ARRIVED, target_id="gateway", data={"request_id": "r3", "path": "/healthz"}))

    engine.run(until=0.5)

    assert auth_srv.completed == 1
    assert order_srv.completed == 1
    assert default_srv.completed == 1

def test_autoscaling_group_scaling():
    """Verify AutoscalingGroup scales up server concurrency under sustained load."""
    engine = SimulationEngine(seed=42)
    server = APIServer("srv_auto", concurrency=2, latency=0.1, max_queue_depth=50)
    asg = AutoscalingGroup(
        "asg",
        target_component_id="srv_auto",
        min_capacity=2,
        max_capacity=8,
        scale_up_threshold=0.60,
        cooldown=0.2,
    )

    client = Client("cli_auto", "srv_auto", rate_per_sec=30.0)

    engine.register_component(server)
    engine.register_component(asg)
    engine.register_component(client)

    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="cli_auto"))
    # Run long enough for saturation and scaling evaluation
    for t in [0.2, 0.5, 0.8, 1.1]:
        engine.schedule(Event(time=t, type=EventType.REQUEST_ARRIVED, target_id="asg"))

    engine.run(until=1.5)

    # Capacity should have scaled up beyond min_capacity
    assert asg.current_capacity > asg.min_capacity
    assert server.concurrency == asg.current_capacity

# -------------------------------------------------------------
# 3. Cache TTL, LRU Eviction & Cold-Start Stampede Tests
# -------------------------------------------------------------

def test_cache_lru_eviction_and_ttl():
    """Verify Cache LRU capacity eviction and TTL expiration."""
    cache = AdvancedCacheModel(capacity=3, default_ttl=1.0)

    cache.put("k1", "v1", current_time=0.0)
    cache.put("k2", "v2", current_time=0.1)
    cache.put("k3", "v3", current_time=0.2)

    # Access k1 to make it most recently used
    assert cache.get("k1", current_time=0.3) == "v1"

    # Insert k4: capacity 3 exceeded, k2 (least recently used) should be evicted
    cache.put("k4", "v4", current_time=0.4)
    assert cache.evictions == 1
    assert cache.get("k2", current_time=0.5) is None  # evicted!
    assert cache.get("k1", current_time=0.5) == "v1"
    assert cache.get("k3", current_time=0.5) == "v3"
    assert cache.get("k4", current_time=0.5) == "v4"

    # Advance time past TTL (1.0s after put)
    assert cache.get("k3", current_time=1.5) is None  # expired!
    assert cache.expirations == 1

def test_cache_stampede_cold_start():
    """
    Verify cold-start behavior: when cache restarts cold, effective hit rate is 0%,
    causing traffic to bypass cache into backend until warmup finishes.
    """
    cache = AdvancedCacheModel(capacity=1000, hit_rate=0.80, warmup_duration=5.0)
    cache.reset_cold(current_time=10.0)

    # Immediately after reset (t=10.0), effective hit rate is 0%
    assert cache.get_effective_hit_rate(10.0) == 0.0

    # Halfway through warmup (t=12.5), effective hit rate is half of nominal (40%)
    assert abs(cache.get_effective_hit_rate(12.5) - 0.40) < 1e-4

    # Fully warmed up (t=15.0), hit rate reaches nominal 80%
    assert abs(cache.get_effective_hit_rate(15.0) - 0.80) < 1e-4

# -------------------------------------------------------------
# 4. Traffic Profiles Tests
# -------------------------------------------------------------

def test_traffic_profiles():
    """Verify instantaneous rate calculations across all traffic patterns."""
    # 1. Ramp: 10 -> 50 over 10s
    p_ramp = TrafficProfile(pattern_type=TrafficPatternType.RAMP, base_rate=10.0, peak_rate=50.0, ramp_duration=10.0)
    assert p_ramp.get_rate(0.0) == 10.0
    assert p_ramp.get_rate(5.0) == 30.0
    assert p_ramp.get_rate(10.0) == 50.0
    assert p_ramp.get_rate(15.0) == 50.0

    # 2. Step Spike: base 10, spike 100 between t=5 and t=10
    p_spike = TrafficProfile(pattern_type=TrafficPatternType.STEP_SPIKE, base_rate=10.0, peak_rate=100.0, spike_start=5.0, spike_end=10.0)
    assert p_spike.get_rate(2.0) == 10.0
    assert p_spike.get_rate(7.0) == 100.0
    assert p_spike.get_rate(12.0) == 10.0

    # 3. Bursty: 2s on (50), 3s off (10)
    p_burst = TrafficProfile(pattern_type=TrafficPatternType.BURSTY, base_rate=10.0, peak_rate=50.0, burst_on_duration=2.0, burst_off_duration=3.0)
    assert p_burst.get_rate(1.0) == 50.0
    assert p_burst.get_rate(3.0) == 10.0
    assert p_burst.get_rate(6.0) == 50.0
