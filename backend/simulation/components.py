import uuid
from typing import List, Optional, Dict, Any
from .events import Event, EventType

class BaseComponent:
    def __init__(self, id: str):
        self.id = id
        self.engine = None
        self.dropped = 0
        self.completed = 0

    def handle_event(self, event: Event):
        pass

    def get_state(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dropped": self.dropped,
            "completed": self.completed
        }

class Client(BaseComponent):
    def __init__(self, id: str, target_id: str, rate_per_sec: float):
        super().__init__(id)
        self.target_id = target_id
        self.rate_per_sec = rate_per_sec
        self.sent = 0

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            req_id = str(uuid.uuid4())
            self.sent += 1
            self.engine.schedule(Event(
                time=self.engine.time,
                type=EventType.REQUEST_ARRIVED,
                target_id=self.target_id,
                data={"request_id": req_id, "source": self.id}
            ))
            next_time = self.engine.time + (1.0 / self.rate_per_sec)
            self.engine.schedule(Event(
                time=next_time,
                type=EventType.REQUEST_ARRIVED,
                target_id=self.id
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["sent"] = self.sent
        return state

class LoadBalancer(BaseComponent):
    def __init__(self, id: str, backend_ids: List[str]):
        super().__init__(id)
        self.backend_ids = backend_ids
        self.index = 0

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            if not self.backend_ids:
                self.dropped += 1
                self.engine.metrics["failed"] += 1
                return
            
            target = self.backend_ids[self.index]
            self.index = (self.index + 1) % len(self.backend_ids)
            
            self.engine.schedule(Event(
                time=self.engine.time,
                type=EventType.REQUEST_ARRIVED,
                target_id=target,
                data=event.data
            ))

class APIServer(BaseComponent):
    def __init__(self, id: str, capacity: int, latency: float, db_id: Optional[str] = None):
        super().__init__(id)
        self.capacity = capacity
        self.latency = latency
        self.db_id = db_id
        self.active_requests = 0

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            if self.active_requests >= self.capacity:
                self.dropped += 1
                self.engine.metrics["dropped"] += 1
                return
            
            self.active_requests += 1
            if self.db_id:
                self.engine.schedule(Event(
                    time=self.engine.time + self.latency / 2,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=self.db_id,
                    data={"request_id": event.data["request_id"], "api_id": self.id}
                ))
            else:
                self.engine.schedule(Event(
                    time=self.engine.time + self.latency,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=self.id,
                    data=event.data
                ))
                
        elif event.type == EventType.REQUEST_COMPLETED:
            self.active_requests -= 1
            self.completed += 1
            self.engine.metrics["completed"] += 1

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.capacity
        return state

class Database(BaseComponent):
    def __init__(self, id: str, capacity: int, latency: float):
        super().__init__(id)
        self.capacity = capacity
        self.latency = latency
        self.active_requests = 0

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            if self.active_requests >= self.capacity:
                self.dropped += 1
                self.engine.metrics["dropped"] += 1
                return
                
            self.active_requests += 1
            
            self.engine.schedule(Event(
                time=self.engine.time + self.latency,
                type=EventType.REQUEST_COMPLETED,
                target_id=self.id,
                data=event.data
            ))
            
        elif event.type == EventType.REQUEST_COMPLETED:
            self.active_requests -= 1
            self.completed += 1
            self.engine.schedule(Event(
                time=self.engine.time,
                type=EventType.REQUEST_COMPLETED,
                target_id=event.data["api_id"],
                data=event.data
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.capacity
        return state

class Cache(BaseComponent):
    def __init__(self, id: str, db_id: str, hit_rate: float = 0.8, latency: float = 0.01):
        super().__init__(id)
        self.db_id = db_id
        self.hit_rate = hit_rate
        self.latency = latency
        self.hits = 0
        self.misses = 0

    def handle_event(self, event: Event):
        import random
        if event.type == EventType.REQUEST_ARRIVED:
            if random.random() < self.hit_rate:
                self.hits += 1
                self.engine.schedule(Event(
                    time=self.engine.time + self.latency,
                    type=EventType.REQUEST_COMPLETED,
                    target_id=event.data.get("api_id") or self.id,
                    data=event.data
                ))
            else:
                self.misses += 1
                if self.db_id:
                    self.engine.schedule(Event(
                        time=self.engine.time + self.latency,
                        type=EventType.REQUEST_ARRIVED,
                        target_id=self.db_id,
                        data=event.data
                    ))
                else:
                    self.dropped += 1
        elif event.type == EventType.REQUEST_COMPLETED:
            self.completed += 1
            self.engine.schedule(Event(
                time=self.engine.time,
                type=EventType.REQUEST_COMPLETED,
                target_id=event.data.get("api_id") or self.id,
                data=event.data
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["hits"] = self.hits
        state["misses"] = self.misses
        return state

class MessageQueue(BaseComponent):
    def __init__(self, id: str, max_depth: int = 1000):
        super().__init__(id)
        self.max_depth = max_depth
        self.queue = []
        self.workers = []

    def register_worker(self, worker_id: str):
        self.workers.append(worker_id)

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            if len(self.queue) >= self.max_depth:
                self.dropped += 1
                self.engine.metrics["dropped"] += 1
                return
            self.queue.append(event.data)
            self._try_dispatch()
        elif event.type == EventType.REQUEST_COMPLETED:
            self.completed += 1
            self._try_dispatch()

    def _try_dispatch(self):
        if not self.queue: return
        for wid in self.workers:
            w = self.engine.components.get(wid)
            if w and w.active_requests < w.capacity:
                data = self.queue.pop(0)
                self.engine.schedule(Event(
                    time=self.engine.time,
                    type=EventType.REQUEST_ARRIVED,
                    target_id=wid,
                    data=data
                ))
                break

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["queue_depth"] = len(self.queue)
        state["max_depth"] = self.max_depth
        return state

class Worker(BaseComponent):
    def __init__(self, id: str, queue_id: str, capacity: int = 5, latency: float = 1.0):
        super().__init__(id)
        self.queue_id = queue_id
        self.capacity = capacity
        self.latency = latency
        self.active_requests = 0

    def handle_event(self, event: Event):
        if event.type == EventType.REQUEST_ARRIVED:
            self.active_requests += 1
            self.engine.schedule(Event(
                time=self.engine.time + self.latency,
                type=EventType.REQUEST_COMPLETED,
                target_id=self.id,
                data=event.data
            ))
        elif event.type == EventType.REQUEST_COMPLETED:
            self.active_requests -= 1
            self.completed += 1
            self.engine.metrics["completed"] += 1
            self.engine.schedule(Event(
                time=self.engine.time,
                type=EventType.REQUEST_COMPLETED,
                target_id=self.queue_id,
                data=event.data
            ))

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["active"] = self.active_requests
        state["capacity"] = self.capacity
        return state
