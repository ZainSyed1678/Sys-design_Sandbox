from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, field

class EventType(str, Enum):
    REQUEST_ARRIVED = "REQUEST_ARRIVED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    REQUEST_FAILED = "REQUEST_FAILED"
    COMPONENT_FAILED = "COMPONENT_FAILED"
    COMPONENT_RECOVERED = "COMPONENT_RECOVERED"
    TRAFFIC_CHANGED = "TRAFFIC_CHANGED"

@dataclass
class Event:
    time: float
    type: EventType
    target_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    event_id: int = 0

    def __lt__(self, other: 'Event') -> bool:
        if self.time != other.time:
            return self.time < other.time
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.event_id < other.event_id
