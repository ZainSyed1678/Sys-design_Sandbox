import uuid
import threading
import time
from enum import Enum
from typing import Dict, Any, Optional

from simulation.engine import SimulationEngine
from simulation.components import Client, LoadBalancer, APIServer, Database, Cache, MessageQueue, Worker
from simulation.rich_components import ReadReplicaDatabase, ShardedDatabase, CDN, APIGateway, AutoscalingGroup
from simulation.distributions import Distribution, DistributionType
from simulation.resilience import CircuitBreaker, TokenBucket, RetryPolicy
from simulation.traffic import TrafficProfile
from simulation.events import Event, EventType
from extensions import socketio
from core.analyzer import analyzer

class SimState(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SimulationInstance:
    def __init__(self, sim_id: str, graph: Dict[str, Any]):
        self.sim_id = sim_id
        self.graph = graph
        self.state = SimState.CREATED
        seed = int(graph.get("seed", 42))
        self.engine = SimulationEngine(seed=seed)
        self.thread = None
        self._stop_event = threading.Event()

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
        socketio.emit('SIM_STARTED', {'sim_id': self.sim_id})

        while not self._stop_event.is_set():
            step_until = self.engine.time + 0.5
            self.engine.run(until=step_until)

            states = self.engine.get_component_states()
            analysis = analyzer.analyze(states, self.engine.metrics)

            socketio.emit('METRICS_UPDATE', {
                'sim_id': self.sim_id,
                'time': round(self.engine.time, 4),
                'metrics': self.engine.metrics,
                'components': states,
                'analysis': analysis
            })

            time.sleep(0.5)

        self.state = SimState.STOPPED
        socketio.emit('SIM_STOPPED', {'sim_id': self.sim_id})

    def start(self):
        if self.state in [SimState.RUNNING, SimState.FAILED]:
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if self.state == SimState.RUNNING:
            self._stop_event.set()
            if self.thread:
                self.thread.join(timeout=2.0)
            self.state = SimState.STOPPED

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "sim_time": round(self.engine.time, 4),
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

    def create_simulation(self, graph: Dict[str, Any]) -> str:
        sim_id = str(uuid.uuid4())
        instance = SimulationInstance(sim_id, graph)
        instance.build()
        self.simulations[sim_id] = instance
        return sim_id

    def get_simulation(self, sim_id: str) -> Optional[SimulationInstance]:
        return self.simulations.get(sim_id)

sim_manager = SimulationManager()
