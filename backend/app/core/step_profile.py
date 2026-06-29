import json
from dataclasses import asdict, dataclass


@dataclass
class StepProfile:
    redis_get_ms: float = 0.0
    business_ms: float = 0.0
    redis_set_ms: float = 0.0
    serialization_ms: float = 0.0

    @property
    def accounted_ms(self) -> float:
        return self.redis_get_ms + self.business_ms + self.redis_set_ms + self.serialization_ms

    def as_header_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_header_value(cls, value: str) -> "StepProfile":
        return cls(**json.loads(value))
