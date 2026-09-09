import heapq
from typing import List, Dict, Any
from .events import Event

class SimulationEngine:
    def __init__(self):
        self.time: float = 0.0
        self.events: List[Event] = []
        self.components: Dict[str, Any] = {}
        self.metrics = {
            "completed": 0,
            "failed": 0,
            "dropped": 0
        }

    def register_component(self, component: Any):
        self.components[component.id] = component
        component.engine = self

    def schedule(self, event: Event):
        heapq.heappush(self.events, event)

    def run(self, until: float):
        while self.events and self.events[0].time <= until:
            event = heapq.heappop(self.events)
            self.time = event.time
            target = self.components.get(event.target_id)
            if target:
                target.handle_event(event)
            else:
                self.metrics["dropped"] += 1

    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        return {cid: comp.get_state() for cid, comp in self.components.items()}
