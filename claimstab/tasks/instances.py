from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class ProblemInstance:
    instance_id: str
    payload: Any
    meta: Dict[str, Any] | None = None