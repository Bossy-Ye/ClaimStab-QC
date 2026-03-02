# claimstab/methods/spec.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class MethodSpec:
    """Task-agnostic method specification."""

    name: str
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    # Backward-compatible alias for old QAOA-only paths.
    p: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("MethodSpec.name must be a non-empty string.")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("MethodSpec.kind must be a non-empty string.")
        if not isinstance(self.params, Mapping):
            raise ValueError("MethodSpec.params must be a mapping.")
        if self.p is not None and "p" not in self.params:
            merged = dict(self.params)
            merged["p"] = self.p
            object.__setattr__(self, "params", merged)
