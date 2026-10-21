import math
from typing import List, Optional, Dict, Any
from .events import Event, EventType
from .distributions import Distribution, DistributionType
from .engine import calculate_percentiles

class BaseComponent:
    def __init__(self, id: str):
        self.id = id
        self.engine = None
        self.is_healthy = True
        self.dropped = 0
        self.completed = 0
        self.failed = 0

        # Area integrals for exact queueing theory statistics
        self.area_busy: float = 0.0
        self.area_queue: float = 0.0
        self.area_system: float = 0.0
        self.last_area_time: float = 0.0

        # Latency tracking
        self.completed_latencies: List[float] = []
        self.queue_wait_times: List[float] = []
        self.service_times: List[float] = []

    def _update_areas(self):
        """Update continuous area integrals up to the current simulation time."""
        if not self.engine:
            return
        curr = self.engine.time
        dt = curr - self.last_area_time
        if dt > 0:
            active = getattr(self, "active_requests", 0)
            q_len = len(getattr(self, "waiting_queue", []))
            self.area_busy += active * dt
            self.area_queue += q_len * dt
            self.area_system += (active + q_len) * dt
            self.last_area_time = curr

    def get_utilization(self) -> float:
        """
        Server utilization rho = time-average busy servers / concurrency.
        """
        self._update_areas()
        if not self.engine or self.engine.time <= 0:
            return 0.0
        c = getattr(self, "concurrency", 1)
        if c <= 0:
            return 0.0
        return min(1.0, max(0.0, self.area_busy / (c * self.engine.time)))

    def get_throughput(self) -> float:
        """Completed requests per unit virtual time."""
        if not self.engine or self.engine.time <= 0:
            return 0.0
        return self.completed / self.engine.time

    def get_drop_rate(self) -> float:
        """Ratio of dropped requests to total processed requests."""
        total = self.completed + self.dropped
        if total <= 0:
            return 0.0
        return self.dropped / total

    def get_mean_queue_length(self) -> float:
        """Time-average number of requests in waiting queue (L_q)."""
        self._update_areas()
        if not self.engine or self.engine.time <= 0:
            return 0.0
        return self.area_queue / self.engine.time

    def get_mean_system_occupancy(self) -> float:
        """Time-average number of requests in component (L)."""
        self._update_areas()
        if not self.engine or self.engine.time <= 0:
            return 0.0
        return self.area_system / self.engine.time

    def handle_event(self, event: Event) -> bool:
        self._update_areas()
        if event.type == EventType.COMPONENT_FAILED:
            self.is_healthy = False
            return False
        elif event.type == EventType.COMPONENT_RECOVERED:
            self.is_healthy = True
            return False

        if not self.is_healthy and event.type == EventType.REQUEST_ARRIVED:
            self.dropped += 1
            if self.engine:
                self.engine.record_request_dropped(event.data, self.id, "component_unhealthy")
            return False

        return True

    def get_state(self) -> Dict[str, Any]:
        self._update_areas()
        lat_pct = calculate_percentiles(self.completed_latencies)
        return {
            "id": self.id,
            "healthy": self.is_healthy,
            "dropped": self.dropped,
            "completed": self.completed,
            "failed": self.failed,
            "utilization": round(self.get_utilization(), 4),
            "throughput": round(self.get_throughput(), 4),
            "drop_rate": round(self.get_drop_rate(), 4),
            "latency_p50": lat_pct["p50"],
            "latency_p95": lat_pct["p95"],
            "latency_p99": lat_pct["p99"],
            "latency_mean": lat_pct["mean"],
            "mean_queue_length": round(self.get_mean_queue_length(), 4),
            "mean_system_occupancy": round(self.get_mean_system_occupancy(), 4),
        }


class Client(BaseComponent):
    def __init__(
        self,
        id: str,
        target_id: str,
        rate_per_sec: float = 10.0,
        arrival_dist: Optional[Distribution] = None,
        arrival_process: Optional[str] = None,
    ):
        super().__init__(id)
        self.target_id = target_id
        self.rate_per_sec = max(1e-9, float(rate_per_sec))
        if arrival_dist is not None:
            self.arrival_dist = arrival_dist
        elif arrival_process == "poisson":
            self.arrival_dist = Distribution(DistributionType.EXPONENTIAL, mean=1.0 / self.rate_per_sec)
        elif arrival_process == "constant":
            self.arrival_dist = Distribution(DistributionType.CONSTANT, mean=1.0 / self.rate_per_sec)
        else:
            self.arrival_dist = Distribution(DistributionType.CONSTANT, mean=1.0 / self.rate_per_sec)
        self.sent = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.TRAFFIC_CHANGED:
            self.rate_per_sec = max(1e-9, float(event.data.get("rate_per_sec", self.rate_per_sec)))
            self.arrival_dist.mean = 1.0 / self.rate_per_sec

        elif event.type == EventType.REQUEST_ARRIVED:
            # Deterministic request ID generation
            req_id = self.engine.next_request_id(prefix=f"req_{self.id}") if self.engine else f"req_{self.id}_{self.sent}"
            self.sent += 1

            req_data = {
                "request_id": req_id,
                "source": self.id,
                "client_id": self.id,
                "created_at": self.engine.time if self.engine else 0.0,
                "hops": [],
            }

            # Forward request to downstream target
            if self.engine:
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=self.target_id,
                    data=req_data,
                ))

                # Schedule next arrival driven by PRNG distribution
                interval = self.arrival_dist.sample(self.engine.rng)
                self.engine.schedule(Event(
                    time=self.engine.time + interval,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=self.id,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["sent"] = self.sent
        state["rate_per_sec"] = self.rate_per_sec
        state["arrival_process"] = self.arrival_dist.dist_type.value
        return state


class LoadBalancer(BaseComponent):
    def __init__(self, id: str, backend_ids: List[str], strategy: str = "round_robin"):
        super().__init__(id)
        self.backend_ids = list(backend_ids)
        self.strategy = strategy
        self.index = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return
        if event.type == EventType.REQUEST_ARRIVED:
            if not self.backend_ids:
                self.dropped += 1
                if self.engine:
                    self.engine.record_request_dropped(event.data, self.id, "no_backends")
                return

            target = self.backend_ids[self.index]
            self.index = (self.index + 1) % len(self.backend_ids)

            if self.engine:
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=target,
                    data=event.data,
                ))


class APIServer(BaseComponent):
    def __init__(
        self,
        id: str,
        concurrency: Optional[int] = None,
        capacity: Optional[int] = None,
        latency: float = 0.1,
        service_dist: Optional[Distribution] = None,
        max_queue_depth: Optional[int] = 0,
        db_id: Optional[str] = None,
    ):
        super().__init__(id)
        self.concurrency = concurrency if concurrency is not None else (capacity if capacity is not None else 10)
        self.capacity = self.concurrency  # Backwards compatibility
        self.latency = float(latency)
        if service_dist is not None:
            self.service_dist = service_dist
        else:
            self.service_dist = Distribution(DistributionType.CONSTANT, mean=self.latency)
        self.max_queue_depth = max_queue_depth  # None = unbounded, 0 = loss system, >0 = bounded queue
        self.db_id = db_id
        self.active_requests: int = 0
        self.waiting_queue: List[Dict[str, Any]] = []

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            req_data = event.data

            if self.active_requests < self.concurrency:
                # Immediate service
                self.active_requests += 1
                self.queue_wait_times.append(0.0)
                self._start_service(req_data, queue_wait=0.0)
            else:
                # Server busy: check queue capacity
                if self.max_queue_depth is None or len(self.waiting_queue) < self.max_queue_depth:
                    self.waiting_queue.append({
                        "data": req_data,
                        "queued_at": self.engine.time if self.engine else 0.0,
                    })
                else:
                    self.dropped += 1
                    if self.engine:
                        self.engine.record_request_dropped(req_data, self.id, "queue_full")

        elif event.type == EventType.REQUEST_COMPLETED:
            req_data = event.data

            # Check if this completion is returning from a downstream DB
            if req_data.get("_awaiting_db_return", False):
                req_data["_awaiting_db_return"] = False
                rem_dur = req_data.pop("_remaining_service", 0.0)
                if rem_dur > 0:
                    self.engine.schedule(Event(
                        time=self.engine.time + rem_dur,
                        type=EventType.REQUEST_COMPLETED,
                        target_id=self.id,
                        data=req_data,
                    ))
                    return

            # Request finished processing at this server
            self.active_requests = max(0, self.active_requests - 1)
            self.completed += 1

            # Complete hop tracking
            hop = req_data.get("_current_hop", {})
            if hop:
                hop_dur = self.engine.time - hop.get("arrived_at", self.engine.time)
                self.completed_latencies.append(hop_dur)
                req_data.setdefault("hops", []).append(hop)
                req_data.pop("_current_hop", None)

            # Record system-wide completion if terminal
            if self.engine:
                self.engine.record_request_completion(req_data)

            # Dequeue next waiting request if queue is non-empty
            if self.waiting_queue and self.active_requests < self.concurrency:
                next_item = self.waiting_queue.pop(0)
                self.active_requests += 1
                q_wait = max(0.0, self.engine.time - next_item["queued_at"])
                self.queue_wait_times.append(q_wait)
                self._start_service(next_item["data"], queue_wait=q_wait)

    def _start_service(self, req_data: Dict[str, Any], queue_wait: float):
        dur = self.service_dist.sample(self.engine.rng) if self.engine else self.latency
        self.service_times.append(dur)

        req_data["_current_hop"] = {
            "component_id": self.id,
            "arrived_at": (self.engine.time - queue_wait) if self.engine else 0.0,
            "queue_wait": queue_wait,
            "service_start": self.engine.time if self.engine else 0.0,
            "service_duration": dur,
        }

        if self.db_id and self.engine:
            # Multi-tier call: half latency before DB, downstream call, half latency on return
            req_data["_awaiting_db_return"] = True
            req_data["_remaining_service"] = dur / 2.0
            req_data["api_id"] = self.id
            self.engine.schedule(Event(
                time=self.engine.time + (dur / 2.0),
                type=EventType.REQUEST_ARRIVED,
                target_id=self.db_id,
                data=req_data,
            ))
        elif self.engine:
            self.engine.schedule(Event(
                time=self.engine.time + dur,
                type=EventType.REQUEST_COMPLETED,
                target_id=self.id,
                data=req_data,
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.concurrency
        state["concurrency"] = self.concurrency
        state["queue_depth"] = len(self.waiting_queue)
        state["max_queue_depth"] = self.max_queue_depth
        state["service_distribution"] = self.service_dist.dist_type.value
        state["mean_service_time"] = self.service_dist.mean
        q_pct = calculate_percentiles(self.queue_wait_times)
        state["queue_wait_p50"] = q_pct["p50"]
        state["queue_wait_p95"] = q_pct["p95"]
        state["queue_wait_mean"] = q_pct["mean"]
        return state


class Database(BaseComponent):
    def __init__(
        self,
        id: str,
        concurrency: Optional[int] = None,
        capacity: Optional[int] = None,
        latency: float = 0.2,
        service_dist: Optional[Distribution] = None,
        max_queue_depth: Optional[int] = 0,
    ):
        super().__init__(id)
        self.concurrency = concurrency if concurrency is not None else (capacity if capacity is not None else 5)
        self.capacity = self.concurrency  # Backwards compatibility
        self.latency = float(latency)
        if service_dist is not None:
            self.service_dist = service_dist
        else:
            self.service_dist = Distribution(DistributionType.CONSTANT, mean=self.latency)
        self.max_queue_depth = max_queue_depth
        self.active_requests: int = 0
        self.waiting_queue: List[Dict[str, Any]] = []

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            req_data = event.data

            if self.active_requests < self.concurrency:
                self.active_requests += 1
                self.queue_wait_times.append(0.0)
                self._start_service(req_data, queue_wait=0.0)
            else:
                if self.max_queue_depth is None or len(self.waiting_queue) < self.max_queue_depth:
                    self.waiting_queue.append({
                        "data": req_data,
                        "queued_at": self.engine.time if self.engine else 0.0,
                    })
                else:
                    self.dropped += 1
                    if self.engine:
                        self.engine.record_request_dropped(req_data, self.id, "queue_full")

        elif event.type == EventType.REQUEST_COMPLETED:
            req_data = event.data
            self.active_requests = max(0, self.active_requests - 1)
            self.completed += 1

            # Complete DB hop
            hop = req_data.get("_db_hop", {})
            if hop:
                hop_dur = self.engine.time - hop.get("arrived_at", self.engine.time)
                self.completed_latencies.append(hop_dur)
                req_data.setdefault("hops", []).append(hop)
                req_data.pop("_db_hop", None)

            # Return response to upstream caller (APIServer) if designated
            api_id = req_data.get("api_id")
            if api_id and self.engine:
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=api_id,
                    data=req_data,
                ))
            elif self.engine:
                self.engine.record_request_completion(req_data)

            # Dequeue next waiting request
            if self.waiting_queue and self.active_requests < self.concurrency:
                next_item = self.waiting_queue.pop(0)
                self.active_requests += 1
                q_wait = max(0.0, self.engine.time - next_item["queued_at"])
                self.queue_wait_times.append(q_wait)
                self._start_service(next_item["data"], queue_wait=q_wait)

    def _start_service(self, req_data: Dict[str, Any], queue_wait: float):
        dur = self.service_dist.sample(self.engine.rng) if self.engine else self.latency
        self.service_times.append(dur)

        req_data["_db_hop"] = {
            "component_id": self.id,
            "arrived_at": (self.engine.time - queue_wait) if self.engine else 0.0,
            "queue_wait": queue_wait,
            "service_start": self.engine.time if self.engine else 0.0,
            "service_duration": dur,
        }

        if self.engine:
            self.engine.schedule(Event(
                time=self.engine.time + dur,
                type=EventType.REQUEST_COMPLETED,
                target_id=self.id,
                data=req_data,
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.concurrency
        state["concurrency"] = self.concurrency
        state["queue_depth"] = len(self.waiting_queue)
        state["max_queue_depth"] = self.max_queue_depth
        state["service_distribution"] = self.service_dist.dist_type.value
        state["mean_service_time"] = self.service_dist.mean
        q_pct = calculate_percentiles(self.queue_wait_times)
        state["queue_wait_p50"] = q_pct["p50"]
        state["queue_wait_p95"] = q_pct["p95"]
        state["queue_wait_mean"] = q_pct["mean"]
        return state


class Cache(BaseComponent):
    def __init__(self, id: str, db_id: Optional[str] = None, hit_rate: float = 0.8, latency: float = 0.01):
        super().__init__(id)
        self.db_id = db_id
        self.hit_rate = float(hit_rate)
        self.latency = float(latency)
        self.hits = 0
        self.misses = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            # Use seeded PRNG from engine
            rng_roll = self.engine.rng.random() if self.engine else 0.5
            if rng_roll < self.hit_rate:
                self.hits += 1
                self.completed += 1
                if self.engine:
                    target = event.data.get("api_id") or self.id
                    self.engine.schedule(Event(
                        time=self.engine.time + self.latency,
                        type=EventType.REQUEST_COMPLETED,
                        target_id=target,
                        data=event.data,
                    ))
            else:
                self.misses += 1
                if self.db_id and self.engine:
                    self.engine.schedule(Event(
                        time=self.engine.time + self.latency,
                        type=EventType.REQUEST_ARRIVED,
                        target_id=self.db_id,
                        data=event.data,
                    ))
                else:
                    self.dropped += 1
                    if self.engine:
                        self.engine.record_request_dropped(event.data, self.id, "cache_miss_no_backend")

        elif event.type == EventType.REQUEST_COMPLETED:
            self.completed += 1
            if self.engine:
                target = event.data.get("api_id") or self.id
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=target,
                    data=event.data,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["hits"] = self.hits
        state["misses"] = self.misses
        state["hit_rate"] = self.hit_rate
        total = self.hits + self.misses
        state["observed_hit_rate"] = round(self.hits / total, 4) if total > 0 else 0.0
        return state


class MessageQueue(BaseComponent):
    def __init__(self, id: str, max_depth: int = 1000):
        super().__init__(id)
        self.max_depth = int(max_depth)
        self.queue: List[Dict[str, Any]] = []
        self.workers: List[str] = []

    def register_worker(self, worker_id: str):
        if worker_id not in self.workers:
            self.workers.append(worker_id)

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            if len(self.queue) >= self.max_depth:
                self.dropped += 1
                if self.engine:
                    self.engine.record_request_dropped(event.data, self.id, "queue_depth_exceeded")
                return
            self.queue.append(event.data)
            self._try_dispatch()

        elif event.type == EventType.REQUEST_COMPLETED:
            self.completed += 1
            self._try_dispatch()

    def _try_dispatch(self):
        if not self.queue or not self.engine:
            return
        for wid in self.workers:
            w = self.engine.components.get(wid)
            if w and getattr(w, "active_requests", 0) < getattr(w, "concurrency", getattr(w, "capacity", 1)):
                data = self.queue.pop(0)
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=wid,
                    data=data,
                ))
                if not self.queue:
                    break

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["queue_depth"] = len(self.queue)
        state["max_depth"] = self.max_depth
        return state


class Worker(BaseComponent):
    def __init__(
        self,
        id: str,
        queue_id: str,
        concurrency: Optional[int] = None,
        capacity: Optional[int] = None,
        latency: float = 1.0,
        service_dist: Optional[Distribution] = None,
    ):
        super().__init__(id)
        self.queue_id = queue_id
        self.concurrency = concurrency if concurrency is not None else (capacity if capacity is not None else 5)
        self.capacity = self.concurrency  # Backwards compatibility
        self.latency = float(latency)
        if service_dist is not None:
            self.service_dist = service_dist
        else:
            self.service_dist = Distribution(DistributionType.CONSTANT, mean=self.latency)
        self.active_requests: int = 0

    def handle_event(self, event: Event):
        if not super().handle_event(event):
            return

        if event.type == EventType.REQUEST_ARRIVED:
            self.active_requests += 1
            dur = self.service_dist.sample(self.engine.rng) if self.engine else self.latency
            self.service_times.append(dur)
            if self.engine:
                self.engine.schedule(Event(
                    time=self.engine.time + dur,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=self.id,
                    data=event.data,
                ))

        elif event.type == EventType.REQUEST_COMPLETED:
            self.active_requests = max(0, self.active_requests - 1)
            self.completed += 1
            if self.engine:
                self.engine.record_request_completion(event.data)
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=self.queue_id,
                    data=event.data,
                ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.concurrency
        state["concurrency"] = self.concurrency
        state["service_distribution"] = self.service_dist.dist_type.value
        return state
