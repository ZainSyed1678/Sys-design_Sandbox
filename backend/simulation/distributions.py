import math
import random
from enum import Enum
from typing import Dict, Any, Optional

class DistributionType(str, Enum):
    CONSTANT = "constant"
    EXPONENTIAL = "exponential"
    LOGNORMAL = "lognormal"
    POISSON = "poisson"

class Distribution:
    """
    Seeded pseudorandom distribution sampler.
    Generates service times or interarrival times according to standard stochastic distributions.
    """
    def __init__(
        self,
        dist_type: DistributionType = DistributionType.CONSTANT,
        mean: float = 0.1,
        sigma: float = 0.5,
    ):
        if isinstance(dist_type, str):
            dist_type = DistributionType(dist_type.lower())
        self.dist_type = dist_type
        self.mean = max(1e-9, float(mean))
        self.sigma = max(1e-9, float(sigma))

    def sample(self, rng: random.Random) -> float:
        """
        Sample a non-negative duration from the distribution using the provided seeded PRNG.
        """
        if self.dist_type == DistributionType.CONSTANT:
            return self.mean
        elif self.dist_type in (DistributionType.EXPONENTIAL, DistributionType.POISSON):
            # For interarrival or service times with mean 1/lambda or mean 1/mu:
            # expovariate(lambd) where lambd = 1.0 / mean
            rate = 1.0 / self.mean
            return max(1e-9, rng.expovariate(rate))
        elif self.dist_type == DistributionType.LOGNORMAL:
            # Calibrate mu such that E[X] = exp(mu + sigma^2 / 2) = self.mean
            # mu = ln(mean) - (sigma^2 / 2)
            mu = math.log(self.mean) - 0.5 * (self.sigma ** 2)
            return max(1e-9, rng.lognormvariate(mu, self.sigma))
        else:
            return self.mean

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.dist_type.value,
            "mean": self.mean,
            "sigma": self.sigma,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Distribution":
        if not data:
            return cls(DistributionType.CONSTANT, 0.1)
        dtype = data.get("type", DistributionType.CONSTANT.value)
        mean = float(data.get("mean", 0.1))
        sigma = float(data.get("sigma", 0.5))
        return cls(DistributionType(dtype), mean, sigma)
