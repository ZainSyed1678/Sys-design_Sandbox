import heapq
import math
import random
from typing import Dict, List, Any, Optional
from .events import Event, EventType

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """
    Compute p50, p95, p99, mean, max, and min from a list of numeric values.
    Uses linear interpolation for percentiles.
    """
    if not values:
        return {
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "mean": 0.0,
            "max": 0.0,
            "min": 0.0,
            "count": 0,
        }
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_vals[int(k)])
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return float(d0 + d1)

    mean_val = sum(sorted_vals) / n
    return {
        "p50": round(percentile(50.0), 6),
        "p95": round(percentile(95.0), 6),
        "p99": round(percentile(99.0), 6),
        "mean": round(mean_val, 6),
        "max": round(sorted_vals[-1], 6),
        "min": round(sorted_vals[0], 6),
        "count": n,
    }


class SimulationEngine:
    def __init__(self, seed: int = 42, time_window_size: float = 1.0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.time: float = 0.0
        self.events: List[Event] = []
        self.components: Dict[str, Any] = {}
        self._event_counter: int = 0
        self._request_counter: int = 0

        # Time series / fixed window tracking
        self.time_window_size: float = max(0.01, float(time_window_size))
        self.current_window_idx: int = 0
        self.window_history: List[Dict[str, Any]] = []
        self._current_window_completed: int = 0
        self._current_window_dropped: int = 0
        self._current_window_latencies: List[float] = []

        # Request completion and drop tracking
        self.completed_latencies: List[float] = []
        self.completed_requests: List[Dict[str, Any]] = []
        self.dropped_requests: List[Dict[str, Any]] = []
        self._metrics_dirty: bool = False

        # Failure modeling & Network partitions (Phase 3)
        self.network_partitions: set = set()

        # Core metrics dictionary (preserves backwards compatibility)
        self._metrics: Dict[str, Any] = {
            "completed": 0,
            "failed": 0,
            "dropped": 0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "latency_mean": 0.0,
            "latency_max": 0.0,
            "throughput": 0.0,
            "drop_rate": 0.0,
            "system_utilization": 0.0,
        }

    @property
    def metrics(self) -> Dict[str, Any]:
        if self._metrics_dirty:
            self._update_system_metrics()
        return self._metrics

    @metrics.setter
    def metrics(self, value: Dict[str, Any]):
        self._metrics = value

    def next_request_id(self, prefix: str = "req") -> str:
        """Generate a deterministic sequential request ID."""
        self._request_counter += 1
        return f"{prefix}_{self._request_counter}"

    def register_component(self, component: Any):
        self.components[component.id] = component
        component.engine = self

    def schedule(self, event: Event):
        """Schedule an event into the priority queue with deterministic tie-breaking."""
        self._event_counter += 1
        event.event_id = self._event_counter
        heapq.heappush(self.events, event)

    def record_request_completion(self, req_data: Dict[str, Any]):
        """Record end-to-end request completion and update metrics."""
        end_time = self.time
        req_data["end_time"] = end_time
        created_at = req_data.get("created_at", end_time)
        latency = max(0.0, end_time - created_at)
        req_data["total_latency"] = latency

        self.completed_requests.append(req_data)
        self.completed_latencies.append(latency)
        self._current_window_completed += 1
        self._current_window_latencies.append(latency)

        self._metrics["completed"] += 1
        self._metrics_dirty = True

    def record_request_dropped(self, req_data: Dict[str, Any], component_id: str, reason: str = "dropped"):
        """Record a dropped request."""
        req_data["dropped_at"] = self.time
        req_data["drop_component"] = component_id
        req_data["drop_reason"] = reason

        self.dropped_requests.append(req_data)
        self._current_window_dropped += 1

        self._metrics["dropped"] += 1
        self._metrics_dirty = True

    def _advance_time_windows(self, target_time: float):
        """Finalize windows as virtual time crosses window boundaries."""
        while (self.current_window_idx + 1) * self.time_window_size <= target_time:
            w_start = self.current_window_idx * self.time_window_size
            w_end = (self.current_window_idx + 1) * self.time_window_size
            w_pct = calculate_percentiles(self._current_window_latencies)
            w_thp = self._current_window_completed / self.time_window_size
            total_reqs = self._current_window_completed + self._current_window_dropped
            w_drop_rate = (self._current_window_dropped / total_reqs) if total_reqs > 0 else 0.0

            self.window_history.append({
                "window_idx": self.current_window_idx,
                "window_start": round(w_start, 4),
                "window_end": round(w_end, 4),
                "completed": self._current_window_completed,
                "dropped": self._current_window_dropped,
                "throughput": round(w_thp, 4),
                "drop_rate": round(w_drop_rate, 4),
                "latency_p50": w_pct["p50"],
                "latency_p95": w_pct["p95"],
                "latency_p99": w_pct["p99"],
                "latency_mean": w_pct["mean"],
                "latency_max": w_pct["max"],
            })

            self.current_window_idx += 1
            self._current_window_completed = 0
            self._current_window_dropped = 0
            self._current_window_latencies = []

    def _update_system_metrics(self):
        """Update aggregate system latency percentiles, throughput, and drop rate."""
        total_completed = self._metrics["completed"]
        total_dropped = self._metrics["dropped"]
        total = total_completed + total_dropped

        if self.completed_latencies:
            pct = calculate_percentiles(self.completed_latencies)
            self._metrics["latency_p50"] = pct["p50"]
            self._metrics["latency_p95"] = pct["p95"]
            self._metrics["latency_p99"] = pct["p99"]
            self._metrics["latency_mean"] = pct["mean"]
            self._metrics["latency_max"] = pct["max"]

        if self.time > 0:
            self._metrics["throughput"] = round(total_completed / self.time, 4)

        if total > 0:
            self._metrics["drop_rate"] = round(total_dropped / total, 4)

        utils = []
        for comp in self.components.values():
            if hasattr(comp, "get_utilization"):
                utils.append(comp.get_utilization())
        if utils:
            self._metrics["system_utilization"] = round(sum(utils) / len(utils), 4)

        self._metrics_dirty = False

    def add_partition(self, u: str, v: str):
        """Sever bidirectional network connectivity between node u and node v."""
        self.network_partitions.add((u, v))
        self.network_partitions.add((v, u))

    def remove_partition(self, u: str, v: str):
        """Restore network connectivity between node u and node v."""
        self.network_partitions.discard((u, v))
        self.network_partitions.discard((v, u))

    def is_partitioned(self, u: str, v: str) -> bool:
        """Check if network transmission between u and v is blocked."""
        return (u, v) in self.network_partitions

    def run(self, until: float):
        """Execute scheduled discrete events up to virtual time 'until'."""
        while self.events and self.events[0].time <= until:
            event = heapq.heappop(self.events)
            self._advance_time_windows(event.time)
            self.time = event.time

            # Handle global network partition events
            if event.type == EventType.NETWORK_PARTITION:
                src = event.data.get("source")
                tgt = event.data.get("target")
                if src and tgt:
                    self.add_partition(src, tgt)
                continue
            elif event.type == EventType.NETWORK_REPAIR:
                src = event.data.get("source")
                tgt = event.data.get("target")
                if src and tgt:
                    self.remove_partition(src, tgt)
                continue

            target = self.components.get(event.target_id)
            if target:
                target.handle_event(event)
            else:
                self.record_request_dropped(event.data, "unknown_component", "target_not_found")

        if self.time < until:
            self._advance_time_windows(until)
            self.time = until

        for comp in self.components.values():
            if hasattr(comp, "_update_areas"):
                comp._update_areas()
        self._update_system_metrics()

    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        self._update_system_metrics()
        states = {}
        for cid, comp in self.components.items():
            states[cid] = comp.get_state()
        return states
