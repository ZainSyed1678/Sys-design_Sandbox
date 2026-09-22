from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, field

class EventType(Enum):
    REQUEST_ARRIVED = "REQUEST_ARRIVED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    REQUEST_FAILED = "REQUEST_FAILED"
    COMPONENT_FAILED = "COMPONENT_FAILED"
    COMPONENT_RECOVERED = "COMPONENT_RECOVERED"
    TRAFFIC_CHANGED = "TRAFFIC_CHANGED"

@dataclass(order=True)
class Event:
    time: float
    type: EventType = field(compare=False)
    target_id: str = field(compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
