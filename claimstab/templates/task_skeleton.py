"""Template: add a new task plugin.

Copy this file and implement your task-specific suite + build logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.instances import ProblemInstance

@dataclass(frozen=True)
class MyPayload:
    num_qubits: int


class MyTaskPlugin:
    """Task plugin contract used by ClaimStab factory/CLI."""

    name = "my_task"

    def __init__(self, **params: Any) -> None:
        self.params = params

    def instances(self, suite: str) -> list[ProblemInstance]:
        """Return problem instances for a suite id."""
        raise NotImplementedError

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow | tuple[Any, Any]:
        """Return BuiltWorkflow(circuit, metric_fn) for one instance + method."""
        raise NotImplementedError
