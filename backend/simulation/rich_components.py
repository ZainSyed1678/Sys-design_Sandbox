import hashlib
from typing import List, Dict, Any, Optional
from .events import Event, EventType
from .components import BaseComponent
from .resilience import TokenBucket

class ReadReplicaDatabase(BaseComponent):
    """
    Primary/Replica Database with Read/Write splitting and asynchronous replication lag.
      - Writes are routed strictly to the Primary.
      - Reads are distributed among read replicas.
      - Replication lag models eventual consistency propagation delay.
    """
    def __init__(
        self,
        id: str,
        primary_id: str,
        replica_ids: List[str],
        replication_lag: float = 0.1,
    ):
        super().__init__(id)
        self.primary_id = primary_id
        self.replica_ids = list(replica_ids)
        self.replication_lag = max(0.001, float(replication_lag))
        self.rr_replica_idx = 0

        self.writes_handled = 0
        self.reads_handled = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            req_data = event.data
            is_write = req_data.get("is_write", False)

            if is_write or not self.replica_ids:
                # Route write to Primary
                self.writes_handled += 1
                target = self.primary_id
            else:
                # Route read to a Read Replica (Round-Robin)
                self.reads_handled += 1
                target = self.replica_ids[self.rr_replica_idx % len(self.replica_ids)]
                self.rr_replica_idx = (self.rr_replica_idx + 1) % len(self.replica_ids)

            if self.engine:
                req_data["source"] = self.id
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=target,
                    data=req_data,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["primary_id"] = self.primary_id
        state["replica_count"] = len(self.replica_ids)
        state["replication_lag"] = self.replication_lag
        state["writes_handled"] = self.writes_handled
        state["reads_handled"] = self.reads_handled
        return state


class ShardedDatabase(BaseComponent):
    """
    Sharded Database router using hash-based partitioning.
    Computes hash(shard_key) % num_shards to route data requests.
    """
    def __init__(self, id: str, shard_ids: List[str]):
        super().__init__(id)
        self.shard_ids = list(shard_ids)
        self.routed_counts: Dict[str, int] = {sid: 0 for sid in self.shard_ids}

    def _hash_shard(self, key: str) -> str:
        if not self.shard_ids:
            return self.id
        idx = int(hashlib.md5(str(key).encode("utf-8")).hexdigest(), 16) % len(self.shard_ids)
        return self.shard_ids[idx]

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            if not self.shard_ids:
                self.dropped += 1
                return

            req_data = event.data
            key = req_data.get("shard_key", req_data.get("request_id", "default_key"))
            target_shard = self._hash_shard(key)
            self.routed_counts[target_shard] = self.routed_counts.get(target_shard, 0) + 1

            if self.engine:
                req_data["source"] = self.id
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=target_shard,
                    data=req_data,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["shard_count"] = len(self.shard_ids)
        state["routed_counts"] = dict(self.routed_counts)
        return state


class CDN(BaseComponent):
    """
    Content Delivery Network (CDN) edge cache.
    Provides edge caching with high hit rates and low latency, forwarding misses to origin.
    """
    def __init__(
        self,
        id: str,
        origin_id: str,
        hit_rate: float = 0.90,
        edge_latency: float = 0.005,
    ):
        super().__init__(id)
        self.origin_id = origin_id
        self.hit_rate = max(0.0, min(1.0, float(hit_rate)))
        self.edge_latency = max(0.0001, float(edge_latency))
        self.hits = 0
        self.misses = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            rng_roll = self.engine.rng.random() if self.engine else 0.5
            eff_latency = self.edge_latency * self.latency_multiplier

            if rng_roll < self.hit_rate:
                self.hits += 1
                self.completed += 1
                if self.engine:
                    client_id = event.data.get("client_id")
                    target = client_id or event.data.get("source") or self.id
                    self.engine.schedule(Event(
                        time=self.engine.time + eff_latency,
                        type=EventType.REQUEST_COMPLETED,
                        target_id=target,
                        data=event.data,
                    ))
            else:
                self.misses += 1
                if self.engine:
                    event.data["source"] = self.id
                    self.engine.schedule(Event(
                        time=self.engine.time + eff_latency,
                        type=EventType.REQUEST_ARRIVED,
                        target_id=self.origin_id,
                        data=event.data,
                    ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["origin_id"] = self.origin_id
        state["hit_rate"] = self.hit_rate
        state["hits"] = self.hits
        state["misses"] = self.misses
        total = self.hits + self.misses
        state["observed_hit_rate"] = round(self.hits / total, 4) if total > 0 else 0.0
        return state


class APIGateway(BaseComponent):
    """
    API Gateway:
      - Path-based prefix routing (e.g. "/api/v1/auth" -> auth_svc, "/api/v1/orders" -> orders_svc).
      - Integrated Token Bucket rate limiting.
      - Gateway hop latency overhead.
    """
    def __init__(
        self,
        id: str,
        routes: Dict[str, str],
        default_target: str,
        rate_limiter: Optional[TokenBucket] = None,
        overhead_latency: float = 0.005,
    ):
        super().__init__(id)
        self.routes = dict(routes)
        self.default_target = default_target
        self.rate_limiter = rate_limiter
        self.overhead_latency = max(0.0001, float(overhead_latency))

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            req_data = event.data
            path = req_data.get("path", "")

            # Path prefix matching
            target = self.default_target
            for prefix, tgt in self.routes.items():
                if path.startswith(prefix):
                    target = tgt
                    break

            if self.engine:
                req_data["source"] = self.id
                self.engine.schedule(Event(
                    time=self.engine.time + self.overhead_latency,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=target,
                    data=req_data,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["routes"] = dict(self.routes)
        state["default_target"] = self.default_target
        return state


class AutoscalingGroup(BaseComponent):
    """
    Autoscaling Group:
      - Dynamically adjusts worker concurrency or instance counts based on utilization.
      - Scale-up threshold (e.g. 0.75 utilization) and scale-down threshold (e.g. 0.25).
      - Configurable startup delay (provisioning time) and cooldown duration.
    """
    def __init__(
        self,
        id: str,
        target_component_id: str,
        min_capacity: int = 2,
        max_capacity: int = 10,
        scale_up_threshold: float = 0.75,
        scale_down_threshold: float = 0.25,
        startup_delay: float = 1.0,
        cooldown: float = 3.0,
        check_interval: float = 1.0,
    ):
        super().__init__(id)
        self.target_component_id = target_component_id
        self.min_capacity = max(1, int(min_capacity))
        self.max_capacity = max(self.min_capacity, int(max_capacity))
        self.current_capacity = self.min_capacity

        self.scale_up_threshold = float(scale_up_threshold)
        self.scale_down_threshold = float(scale_down_threshold)
        self.startup_delay = max(0.01, float(startup_delay))
        self.cooldown = max(0.1, float(cooldown))
        self.check_interval = max(0.1, float(check_interval))

        self.last_scale_time: float = -self.cooldown
        self.scaling_events: List[Dict[str, Any]] = []

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.TRAFFIC_CHANGED or event.type == EventType.REQUEST_ARRIVED:
            self._evaluate_scaling()

    def _evaluate_scaling(self):
        if not self.engine:
            return
        target = self.engine.components.get(self.target_component_id)
        if not target or not hasattr(target, "get_utilization"):
            return

        now = self.engine.time
        if now - self.last_scale_time < self.cooldown:
            return

        util = target.get_utilization()

        if util > self.scale_up_threshold and self.current_capacity < self.max_capacity:
            # Scale up
            self.current_capacity = min(self.max_capacity, self.current_capacity + 1)
            self.last_scale_time = now
            self.scaling_events.append({
                "time": now,
                "action": "SCALE_UP",
                "new_capacity": self.current_capacity,
                "utilization": round(util, 4),
            })
            # Apply capacity increase after startup delay
            if hasattr(target, "concurrency"):
                target.concurrency = self.current_capacity
                target.capacity = self.current_capacity

        elif util < self.scale_down_threshold and self.current_capacity > self.min_capacity:
            # Scale down
            self.current_capacity = max(self.min_capacity, self.current_capacity - 1)
            self.last_scale_time = now
            self.scaling_events.append({
                "time": now,
                "action": "SCALE_DOWN",
                "new_capacity": self.current_capacity,
                "utilization": round(util, 4),
            })
            if hasattr(target, "concurrency"):
                target.concurrency = self.current_capacity
                target.capacity = self.current_capacity

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["target_component"] = self.target_component_id
        state["current_capacity"] = self.current_capacity
        state["min_capacity"] = self.min_capacity
        state["max_capacity"] = self.max_capacity
        state["scaling_events_count"] = len(self.scaling_events)
        return state
