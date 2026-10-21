import math
import random
from enum import Enum
from typing import Dict, Any, Optional

class TrafficPatternType(str, Enum):
    CONSTANT = "constant"
    POISSON = "poisson"
    RAMP = "ramp"
    STEP_SPIKE = "step_spike"
    DIURNAL_SINE = "diurnal_sine"
    BURSTY = "bursty"

class TrafficProfile:
    """
    Evaluates instantaneous arrival rates lambda(t) and interarrival sampling
    according to standard distributed traffic profiles.
    """
    def __init__(
        self,
        pattern_type: TrafficPatternType = TrafficPatternType.CONSTANT,
        base_rate: float = 10.0,
        peak_rate: float = 50.0,
        ramp_duration: float = 10.0,
        spike_start: float = 5.0,
        spike_end: float = 10.0,
        period: float = 60.0,
        burst_on_duration: float = 2.0,
        burst_off_duration: float = 5.0,
    ):
        if isinstance(pattern_type, str):
            pattern_type = TrafficPatternType(pattern_type.lower())
        self.pattern_type = pattern_type
        self.base_rate = max(0.001, float(base_rate))
        self.peak_rate = max(self.base_rate, float(peak_rate))
        self.ramp_duration = max(0.1, float(ramp_duration))
        self.spike_start = float(spike_start)
        self.spike_end = max(self.spike_start, float(spike_end))
        self.period = max(1.0, float(period))
        self.burst_on_duration = max(0.1, float(burst_on_duration))
        self.burst_off_duration = max(0.1, float(burst_off_duration))

    def get_rate(self, current_time: float) -> float:
        """Calculate the instantaneous arrival rate lambda(t) at time t."""
        t = max(0.0, current_time)

        if self.pattern_type in (TrafficPatternType.CONSTANT, TrafficPatternType.POISSON):
            return self.base_rate

        elif self.pattern_type == TrafficPatternType.RAMP:
            if t <= self.ramp_duration:
                fraction = t / self.ramp_duration
                return self.base_rate + (self.peak_rate - self.base_rate) * fraction
            return self.peak_rate

        elif self.pattern_type == TrafficPatternType.STEP_SPIKE:
            if self.spike_start <= t <= self.spike_end:
                return self.peak_rate
            return self.base_rate

        elif self.pattern_type == TrafficPatternType.DIURNAL_SINE:
            amplitude = (self.peak_rate - self.base_rate) / 2.0
            midpoint = self.base_rate + amplitude
            # Sine wave in [base_rate, peak_rate]
            return midpoint + amplitude * math.sin((2.0 * math.pi * t) / self.period)

        elif self.pattern_type == TrafficPatternType.BURSTY:
            cycle = self.burst_on_duration + self.burst_off_duration
            pos = t % cycle
            if pos < self.burst_on_duration:
                return self.peak_rate
            return self.base_rate

        return self.base_rate

    def next_interval(self, current_time: float, rng: random.Random) -> float:
        """Sample the next interarrival duration based on the instantaneous rate."""
        rate = max(0.001, self.get_rate(current_time))
        if self.pattern_type == TrafficPatternType.CONSTANT:
            return 1.0 / rate
        else:
            # Poisson interarrival ~ Exp(rate)
            return rng.expovariate(rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type.value,
            "base_rate": self.base_rate,
            "peak_rate": self.peak_rate,
            "ramp_duration": self.ramp_duration,
            "spike_start": self.spike_start,
            "spike_end": self.spike_end,
            "period": self.period,
            "burst_on_duration": self.burst_on_duration,
            "burst_off_duration": self.burst_off_duration,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TrafficProfile":
        if not data:
            return cls()
        return cls(
            pattern_type=data.get("pattern_type", TrafficPatternType.CONSTANT.value),
            base_rate=float(data.get("base_rate", 10.0)),
            peak_rate=float(data.get("peak_rate", 50.0)),
            ramp_duration=float(data.get("ramp_duration", 10.0)),
            spike_start=float(data.get("spike_start", 5.0)),
            spike_end=float(data.get("spike_end", 10.0)),
            period=float(data.get("period", 60.0)),
            burst_on_duration=float(data.get("burst_on_duration", 2.0)),
            burst_off_duration=float(data.get("burst_off_duration", 5.0)),
        )
