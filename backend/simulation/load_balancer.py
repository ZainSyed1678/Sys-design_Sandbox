import bisect
import hashlib
from enum import Enum
from typing import List, Dict, Optional, Any

class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"
    CONSISTENT_HASHING = "consistent_hashing"

class ConsistentHashRing:
    """
    Deterministic consistent hash ring with virtual nodes (replicas).
    Ensures minimal key remapping when topology changes.
    """
    def __init__(self, nodes: Optional[List[str]] = None, virtual_nodes: int = 50):
        self.virtual_nodes = max(1, int(virtual_nodes))
        self.ring: List[tuple] = []  # sorted list of (hash_int, node_id)
        self.nodes = set()
        if nodes:
            for n in nodes:
                self.add_node(n)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self, node: str):
        if node in self.nodes:
            return
        self.nodes.add(node)
        for i in range(self.virtual_nodes):
            vkey = f"{node}#vn{i}"
            h = self._hash(vkey)
            bisect.insort(self.ring, (h, node))

    def remove_node(self, node: str):
        if node in self.nodes:
            self.nodes.remove(node)
            self.ring = [item for item in self.ring if item[1] != node]

    def get_node(self, key: str) -> Optional[str]:
        if not self.ring:
            return None
        h = self._hash(str(key))
        idx = bisect.bisect_right(self.ring, (h, ""))
        if idx == len(self.ring):
            idx = 0
        return self.ring[idx][1]

class LoadBalancerSelector:
    """
    Implements 5 core load balancing strategies:
      - round_robin
      - least_connections
      - weighted
      - random
      - consistent_hashing
    """
    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        backend_ids: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        virtual_nodes: int = 50,
    ):
        if isinstance(strategy, str):
            strategy = LoadBalancingStrategy(strategy.lower())
        self.strategy = strategy
        self.backend_ids = list(backend_ids or [])
        self.weights = weights or {}
        self.rr_index = 0
        self.hash_ring = ConsistentHashRing(self.backend_ids, virtual_nodes=virtual_nodes)

    def update_backends(self, backends: List[str]):
        self.backend_ids = list(backends)
        self.hash_ring = ConsistentHashRing(self.backend_ids)

    def select(self, engine: Any, req_data: Dict[str, Any]) -> Optional[str]:
        if not self.backend_ids:
            return None

        # Filter out partitioned backends if engine is available
        available = [
            b for b in self.backend_ids
            if not (engine and hasattr(engine, "is_partitioned") and engine.is_partitioned(req_data.get("source", ""), b))
        ]
        if not available:
            available = self.backend_ids

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            chosen = available[self.rr_index % len(available)]
            self.rr_index = (self.rr_index + 1) % len(available)
            return chosen

        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            # Query active requests + queued items on candidate backends
            def get_load(bid: str) -> int:
                comp = engine.components.get(bid) if engine else None
                if not comp:
                    return 0
                active = getattr(comp, "active_requests", 0)
                q_len = len(getattr(comp, "waiting_queue", []))
                return active + q_len

            return min(available, key=get_load)

        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            weights = [max(0.01, float(self.weights.get(b, 1.0))) for b in available]
            if engine and hasattr(engine, "rng"):
                return engine.rng.choices(available, weights=weights, k=1)[0]
            import random
            return random.choices(available, weights=weights, k=1)[0]

        elif self.strategy == LoadBalancingStrategy.RANDOM:
            if engine and hasattr(engine, "rng"):
                return engine.rng.choice(available)
            import random
            return random.choice(available)

        elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASHING:
            key = req_data.get("hash_key", req_data.get("request_id", "default_key"))
            target = self.hash_ring.get_node(key)
            if target in available:
                return target
            return available[0]

        return available[0]
