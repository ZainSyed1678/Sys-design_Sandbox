import uuid
import threading
import time
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Tuple

from simulation.engine import SimulationEngine
from simulation.components import Client, LoadBalancer, APIServer, Database, Cache, MessageQueue, Worker
from simulation.rich_components import ReadReplicaDatabase, ShardedDatabase, CDN, APIGateway, AutoscalingGroup
from simulation.distributions import Distribution, DistributionType
from simulation.resilience import CircuitBreaker, TokenBucket, RetryPolicy
from simulation.traffic import TrafficProfile
from simulation.events import Event, EventType
from extensions import socketio
from core.analyzer import analyzer

# System safety limits
MAX_NODES = 100
MAX_EDGES = 200
MAX_SIM_DURATION = 3600.0       # 1 hour virtual time
MAX_EVENTS = 500_000            # Max events before automatic pause/stop
MAX_CONCURRENT_RUNS = 10        # Max active running threads

class SimState(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

def validate_topology(graph: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates graph topology before starting a simulation:
      - Valid JSON schema with nodes and edges
      - Node and edge count within safety limits
      - At least one client node to generate traffic
      - No dangling edges referencing nonexistent nodes
      - Detects completely disconnected orphan nodes
    Returns (is_valid, error_message).
    """
    if not graph or not isinstance(graph, dict):
        return False, "Topology must be a JSON object with 'nodes' and 'edges'."

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False, "Graph 'nodes' and 'edges' must be lists."

    if len(nodes) == 0:
        return False, "Topology cannot be empty. Please add at least one client node."

    if len(nodes) > MAX_NODES:
        return False, f"Topology exceeds maximum node limit of {MAX_NODES} (found {len(nodes)})."

    if len(edges) > MAX_EDGES:
        return False, f"Topology exceeds maximum edge limit of {MAX_EDGES} (found {len(edges)})."

    node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    if None in node_ids:
        return False, "Every node must have a unique 'id' string."

    # Must contain at least one client node
    has_client = any(n.get("data", {}).get("type") == "client" for n in nodes)
    if not has_client:
        return False, "Topology requires at least one Client node to generate simulated traffic."

    # Validate edges
    connected_nodes: Set[str] = set()
    for e in edges:
        if not isinstance(e, dict):
            return False, "Edges must be JSON objects."
        src = e.get("source")
        tgt = e.get("target")
        if not src or not tgt:
            return False, "Every edge must specify both 'source' and 'target'."
        if src not in node_ids:
            return False, f"Edge '{e.get('id', 'unknown')}' references non-existent source node '{src}'."
        if tgt not in node_ids:
            return False, f"Edge '{e.get('id', 'unknown')}' references non-existent target node '{tgt}'."
        connected_nodes.add(src)
        connected_nodes.add(tgt)

    # Check for orphan nodes if multiple nodes exist
    if len(nodes) > 1:
        orphan_nodes = [nid for nid in node_ids if nid not in connected_nodes]
        if orphan_nodes:
            return False, f"Topology contains unconnected orphan node(s): {', '.join(orphan_nodes)}. Connect them or remove them."

    return True, None


class SimulationInstance:
    def __init__(self, sim_id: str, graph: Dict[str, Any]):
        self.sim_id = sim_id
        self.graph = graph
        self.state = SimState.CREATED
        seed = int(graph.get("seed", 42))
        self.engine = SimulationEngine(seed=seed)
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Set means unpaused/running

        # Speed control: 0.25x to 100x
        self.speed: float = max(0.25, min(100.0, float(graph.get("speed", 1.0))))
        self.step_size: float = 0.5

    def build(self):
        try:
            nodes = self.graph.get("nodes", [])
            edges = self.graph.get("edges", [])

            adj = {}
            for e in edges:
                src = e["source"]
                tgt = e["target"]
                if src not in adj:
                    adj[src] = []
                adj[src].append(tgt)

            for n in nodes:
                nid = n["id"]
                data = n.get("data", {})
                ntype = data.get("type", "unknown")
                targets = adj.get(nid, [])

                if ntype == "client":
                    target_id = targets[0] if targets else "none"
                    rate = float(data.get("rate_per_sec", 10))
                    arr_process = data.get("arrival_process", "poisson")
                    timeout = float(data["timeout"]) if "timeout" in data else None
                    retry_pol = None
                    if "retries" in data:
                        retry_pol = RetryPolicy(
                            max_retries=int(data.get("retries", 3)),
                            base_delay=float(data.get("retry_delay", 0.1)),
                            backoff_type=data.get("backoff_type", "exponential"),
                            retry_budget_ratio=float(data["retry_budget"]) if "retry_budget" in data else None,
                        )
                    cb = None
                    if data.get("circuit_breaker"):
                        cb = CircuitBreaker(
                            failure_threshold=int(data.get("cb_failure_threshold", 5)),
                            recovery_timeout=float(data.get("cb_recovery_timeout", 5.0)),
                        )
                    tb = None
                    if data.get("rate_limit"):
                        tb = TokenBucket(
                            capacity=float(data.get("rate_limit_capacity", 100)),
                            refill_rate=float(data.get("rate_limit_refill", 50)),
                        )
                    comp = Client(
                        nid,
                        target_id,
                        rate_per_sec=rate,
                        arrival_process=arr_process,
                        timeout=timeout,
                        retry_policy=retry_pol,
                        circuit_breaker=cb,
                        rate_limiter=tb,
                    )
                    self.engine.register_component(comp)
                    self.engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id=nid))

                elif ntype == "load_balancer":
                    strategy = data.get("strategy", "round_robin")
                    weights = data.get("weights")
                    comp = LoadBalancer(nid, backend_ids=targets, strategy=strategy, weights=weights)
                    self.engine.register_component(comp)

                elif ntype == "api":
                    db_id = targets[0] if targets else None
                    concurrency = int(data.get("concurrency", data.get("capacity", 10)))
                    latency = float(data.get("latency", 0.1))
                    max_queue = data.get("max_queue_depth", 50)
                    dist_type = data.get("distribution", DistributionType.CONSTANT.value)
                    service_dist = Distribution(dist_type, mean=latency)
                    timeout = float(data["timeout"]) if "timeout" in data else None
                    cb = None
                    if data.get("circuit_breaker"):
                        cb = CircuitBreaker(
                            failure_threshold=int(data.get("cb_failure_threshold", 5)),
                            recovery_timeout=float(data.get("cb_recovery_timeout", 5.0)),
                        )
                    tb = None
                    if data.get("rate_limit"):
                        tb = TokenBucket(
                            capacity=float(data.get("rate_limit_capacity", 100)),
                            refill_rate=float(data.get("rate_limit_refill", 50)),
                        )
                    comp = APIServer(
                        nid,
                        concurrency=concurrency,
                        latency=latency,
                        service_dist=service_dist,
                        max_queue_depth=max_queue,
                        db_id=db_id,
                        timeout=timeout,
                        circuit_breaker=cb,
                        rate_limiter=tb,
                    )
                    self.engine.register_component(comp)

                elif ntype == "database":
                    concurrency = int(data.get("concurrency", data.get("capacity", 5)))
                    latency = float(data.get("latency", 0.2))
                    max_queue = data.get("max_queue_depth", 50)
                    dist_type = data.get("distribution", DistributionType.CONSTANT.value)
                    service_dist = Distribution(dist_type, mean=latency)
                    tb = None
                    if data.get("rate_limit"):
                        tb = TokenBucket(
                            capacity=float(data.get("rate_limit_capacity", 100)),
                            refill_rate=float(data.get("rate_limit_refill", 50)),
                        )
                    comp = Database(
                        nid,
                        concurrency=concurrency,
                        latency=latency,
                        service_dist=service_dist,
                        max_queue_depth=max_queue,
                        rate_limiter=tb,
                    )
                    self.engine.register_component(comp)

                elif ntype == "cache":
                    db_id = targets[0] if targets else None
                    hit_rate = float(data.get("hit_rate", 0.8))
                    latency = float(data.get("latency", 0.01))
                    comp = Cache(nid, db_id=db_id, hit_rate=hit_rate, latency=latency)
                    self.engine.register_component(comp)

                elif ntype == "queue":
                    max_depth = int(data.get("max_depth", 1000))
                    comp = MessageQueue(nid, max_depth=max_depth)
                    for t in targets:
                        comp.register_worker(t)
                    self.engine.register_component(comp)

                elif ntype == "worker":
                    queue_id = "none"
                    for qid, qtargets in adj.items():
                        if nid in qtargets:
                            queue_id = qid
                            break
                    concurrency = int(data.get("concurrency", data.get("capacity", 5)))
                    latency = float(data.get("latency", 1.0))
                    dist_type = data.get("distribution", DistributionType.CONSTANT.value)
                    service_dist = Distribution(dist_type, mean=latency)
                    comp = Worker(nid, queue_id=queue_id, concurrency=concurrency, latency=latency, service_dist=service_dist)
                    self.engine.register_component(comp)

                elif ntype in ("cdn", "edge_cache"):
                    origin = targets[0] if targets else "none"
                    hit_rate = float(data.get("hit_rate", 0.9))
                    edge_lat = float(data.get("latency", 0.005))
                    comp = CDN(nid, origin_id=origin, hit_rate=hit_rate, edge_latency=edge_lat)
                    self.engine.register_component(comp)

                elif ntype == "api_gateway":
                    default_target = targets[0] if targets else "none"
                    routes = data.get("routes", {})
                    tb = None
                    if data.get("rate_limit"):
                        tb = TokenBucket(
                            capacity=float(data.get("rate_limit_capacity", 100)),
                            refill_rate=float(data.get("rate_limit_refill", 50)),
                        )
                    comp = APIGateway(nid, routes=routes, default_target=default_target, rate_limiter=tb)
                    self.engine.register_component(comp)

                elif ntype in ("sharded_database", "sharded_db"):
                    comp = ShardedDatabase(nid, shard_ids=targets)
                    self.engine.register_component(comp)

                elif ntype in ("read_replica", "replicated_db"):
                    primary = targets[0] if targets else "none"
                    replicas = targets[1:] if len(targets) > 1 else []
                    lag = float(data.get("replication_lag", 0.1))
                    comp = ReadReplicaDatabase(nid, primary_id=primary, replica_ids=replicas, replication_lag=lag)
                    self.engine.register_component(comp)

                elif ntype in ("autoscaler", "autoscaling_group"):
                    target_comp = targets[0] if targets else "none"
                    min_cap = int(data.get("min_capacity", 2))
                    max_cap = int(data.get("max_capacity", 10))
                    comp = AutoscalingGroup(nid, target_component_id=target_comp, min_capacity=min_cap, max_capacity=max_cap)
                    self.engine.register_component(comp)

            self.state = SimState.CREATED
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed building topology graph: %s", e)
            self.state = SimState.FAILED

    def _run_loop(self):
        self.state = SimState.RUNNING
        socketio.emit('SIM_STARTED', {'sim_id': self.sim_id}, room=self.sim_id)

        while not self._stop_event.is_set():
            # Wait if paused
            self._pause_event.wait()
            if self._stop_event.is_set():
                break

            # Enforce execution safety limits
            if self.engine.time >= MAX_SIM_DURATION:
                self.state = SimState.COMPLETED
                break
            if self.engine._event_counter >= MAX_EVENTS:
                self.state = SimState.COMPLETED
                break

            step_until = self.engine.time + self.step_size
            self.engine.run(until=step_until)

            states = self.engine.get_component_states()
            analysis = analyzer.analyze(states, self.engine.metrics)

            # Room-scoped broadcast (no cross-session leak)
            socketio.emit('METRICS_UPDATE', {
                'sim_id': self.sim_id,
                'time': round(self.engine.time, 4),
                'metrics': self.engine.metrics,
                'system_history': self.engine.window_history[-30:],
                'components': states,
                'analysis': analysis,
                'state': self.state.value,
                'speed': self.speed,
            }, room=self.sim_id)

            # Real sleep adjusted by speed multiplier
            sleep_duration = max(0.005, self.step_size / self.speed)
            time.sleep(sleep_duration)

        if self.state != SimState.COMPLETED:
            self.state = SimState.STOPPED
        socketio.emit('SIM_STOPPED', {'sim_id': self.sim_id, 'state': self.state.value}, room=self.sim_id)

    def start(self):
        if self.state in [SimState.RUNNING, SimState.FAILED]:
            return
        self._stop_event.clear()
        self._pause_event.set()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def pause(self):
        if self.state == SimState.RUNNING:
            self._pause_event.clear()
            self.state = SimState.PAUSED
            socketio.emit('SIM_PAUSED', {'sim_id': self.sim_id}, room=self.sim_id)

    def resume(self):
        if self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            self._pause_event.set()
            socketio.emit('SIM_RESUMED', {'sim_id': self.sim_id}, room=self.sim_id)

    def step(self, seconds: float = 0.5):
        """Execute simulation forward by seconds and remain paused."""
        if self.state in [SimState.CREATED, SimState.PAUSED]:
            step_until = self.engine.time + max(0.01, float(seconds))
            self.engine.run(until=step_until)
            states = self.engine.get_component_states()
            analysis = analyzer.analyze(states, self.engine.metrics)
            socketio.emit('METRICS_UPDATE', {
                'sim_id': self.sim_id,
                'time': round(self.engine.time, 4),
                'metrics': self.engine.metrics,
                'system_history': self.engine.window_history[-30:],
                'components': states,
                'analysis': analysis,
                'state': self.state.value,
            }, room=self.sim_id)

    def reset(self):
        """Reset simulation state and rebuild topology."""
        self.stop()
        self.engine = SimulationEngine(seed=int(self.graph.get("seed", 42)))
        self.build()
        self.state = SimState.CREATED

    def set_speed(self, speed: float):
        """Set speed multiplier (0.25x to 100.0x)."""
        self.speed = max(0.25, min(100.0, float(speed)))

    def stop(self):
        if self.state in [SimState.RUNNING, SimState.PAUSED]:
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            self.state = SimState.STOPPED

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "sim_time": round(self.engine.time, 4),
            "speed": self.speed,
            "metrics": self.engine.metrics,
            "components": self.engine.get_component_states()
        }

    def inject_event(self, target_id: str, event_type: str, data: Dict[str, Any] = None):
        if self.state != SimState.RUNNING:
            return False
        if not data:
            data = {}
        try:
            etype = EventType(event_type)
            self.engine.schedule(Event(
                time=self.engine.time,
                type=etype,
                target_id=target_id,
                data=data
            ))
            return True
        except ValueError:
            return False


class SimulationManager:
    def __init__(self):
        self.simulations: Dict[str, SimulationInstance] = {}
        self.session_sims: Dict[str, Set[str]] = {}  # sid -> {sim_id, ...}
        self._lock = threading.Lock()

    def create_simulation(self, graph: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Validates graph and creates a simulation instance.
        Returns (sim_id, error_message).
        """
        # 1. Enforce concurrent execution limit
        with self._lock:
            active_runs = sum(1 for s in self.simulations.values() if s.state == SimState.RUNNING)
            if active_runs >= MAX_CONCURRENT_RUNS:
                return None, f"Maximum concurrent active simulations ({MAX_CONCURRENT_RUNS}) reached. Stop an active simulation first."

        # 2. Validate topology
        is_valid, err = validate_topology(graph)
        if not is_valid:
            return None, err

        sim_id = str(uuid.uuid4())
        instance = SimulationInstance(sim_id, graph)
        instance.build()

        if instance.state == SimState.FAILED:
            return None, "Failed to instantiate simulation components from graph."

        with self._lock:
            self.simulations[sim_id] = instance

        return sim_id, None

    def get_simulation(self, sim_id: str) -> Optional[SimulationInstance]:
        with self._lock:
            return self.simulations.get(sim_id)

    def register_client_session(self, sid: str, sim_id: str):
        with self._lock:
            if sid not in self.session_sims:
                self.session_sims[sid] = set()
            self.session_sims[sid].add(sim_id)

    def unregister_client_session(self, sid: str, sim_id: str):
        with self._lock:
            if sid in self.session_sims:
                self.session_sims[sid].discard(sim_id)

    def handle_client_disconnect(self, sid: str):
        """Cleanup running simulations owned by the disconnected client session."""
        with self._lock:
            sim_ids = list(self.session_sims.pop(sid, set()))

        for sim_id in sim_ids:
            sim = self.get_simulation(sim_id)
            if sim:
                sim.stop()
                with self._lock:
                    self.simulations.pop(sim_id, None)

sim_manager = SimulationManager()
