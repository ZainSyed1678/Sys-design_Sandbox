from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict

class EventType(Enum):
    REQUEST_ARRIVED = "REQUEST_ARRIVED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    
@dataclass(order=True)
class Event:
    time: float
    type: EventType = field(compare=False)
    target_id: str = field(compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
