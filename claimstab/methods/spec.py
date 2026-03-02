# claimstab/methods/spec.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class MethodSpec:
    """
    Day-1 scope:
      - kind="qaoa": a QAOA-based workflow variant (parameterized by p)
      - kind="random": a simple random-cut baseline (no quantum circuit)
    """
    name: str
    kind: Literal["qaoa", "random"]
    p: Optional[int] = None  # only used when kind == "qaoa"

    def __post_init__(self) -> None:
        if self.kind == "qaoa" and self.p is None:
            raise ValueError("MethodSpec(kind='qaoa') requires p (e.g., p=1).")
        if self.kind != "qaoa" and self.p is not None:
            raise ValueError("p must be None unless kind == 'qaoa'.")