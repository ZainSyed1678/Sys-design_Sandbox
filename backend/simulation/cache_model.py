from collections import OrderedDict
from typing import Dict, Any, Optional

class AdvancedCacheModel:
    """
    Advanced Cache Model supporting:
      - Fixed capacity with LRU eviction
      - Time-To-Live (TTL) expiration
      - Cold-start warmup period (cache stampede modeling)
      - Key-based caching or synthetic hit-rate sampling
    """
    def __init__(
        self,
        capacity: int = 1000,
        default_ttl: float = 30.0,
        hit_rate: float = 0.8,
        warmup_duration: float = 10.0,
    ):
        self.capacity = max(1, int(capacity))
        self.default_ttl = max(0.1, float(default_ttl))
        self.nominal_hit_rate = max(0.0, min(1.0, float(hit_rate)))
        self.warmup_duration = max(0.0, float(warmup_duration))

        # Storage: key -> {"value": Any, "expires_at": float}
        self.store: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits: int = 0
        self.misses: int = 0
        self.evictions: int = 0
        self.expirations: int = 0
        self.last_reset_time: float = 0.0

    def reset_cold(self, current_time: float):
        """Simulate cache crash / restart into a cold state."""
        self.store.clear()
        self.last_reset_time = current_time

    def get_effective_hit_rate(self, current_time: float) -> float:
        """
        Calculates effective hit rate. During cold start, hit rate ramps
        from 0% up to nominal_hit_rate over warmup_duration.
        """
        if self.warmup_duration <= 0:
            return self.nominal_hit_rate

        time_since_reset = max(0.0, current_time - self.last_reset_time)
        if time_since_reset >= self.warmup_duration:
            return self.nominal_hit_rate

        warmup_fraction = time_since_reset / self.warmup_duration
        return self.nominal_hit_rate * warmup_fraction

    def get(self, key: str, current_time: float) -> Optional[Any]:
        """Look up a key in the cache with TTL expiration check."""
        if key not in self.store:
            self.misses += 1
            return None

        entry = self.store[key]
        if current_time > entry["expires_at"]:
            del self.store[key]
            self.expirations += 1
            self.misses += 1
            return None

        # Cache hit: move to end (MRU)
        self.store.move_to_end(key)
        self.hits += 1
        return entry["value"]

    def put(self, key: str, value: Any, current_time: float, ttl: Optional[float] = None):
        """Insert or update a key with LRU eviction when capacity is reached."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = current_time + effective_ttl

        if key in self.store:
            self.store[key] = {"value": value, "expires_at": expires_at}
            self.store.move_to_end(key)
            return

        # Evict least recently used if at capacity
        if len(self.store) >= self.capacity:
            self.store.popitem(last=False)
            self.evictions += 1

        self.store[key] = {"value": value, "expires_at": expires_at}

    def check_hit_probabilistic(self, current_time: float, rng_roll: float) -> bool:
        """Evaluate a probabilistic hit incorporating cold-start stampede dynamics."""
        effective_rate = self.get_effective_hit_rate(current_time)
        if rng_roll < effective_rate:
            self.hits += 1
            return True
        else:
            self.misses += 1
            return False

    def get_state(self, current_time: float) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self.store),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "observed_hit_rate": round(self.hits / total, 4) if total > 0 else 0.0,
            "effective_hit_rate": round(self.get_effective_hit_rate(current_time), 4),
            "is_warming_up": (current_time - self.last_reset_time) < self.warmup_duration,
        }
