from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.instances import ProblemInstance

Counts = dict[str, int]
MetricFn = Callable[[Counts], float]


class TaskError(RuntimeError):
    """Task plugin related error."""


class TaskSpecError(TaskError):
    """Task specification is invalid."""


@dataclass(frozen=True)
class BuiltWorkflow:
    """Task-built executable workflow for one (instance, method)."""

    circuit: Any
    metric_fn: MetricFn


class TaskPlugin(Protocol):
    """Stable plugin contract for tasks."""

    name: str

    def instances(self, suite: str) -> list[ProblemInstance]:
        """Return benchmark instances for the requested suite id."""

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow | tuple[Any, MetricFn]:
        """Build one executable workflow for a given instance + method."""
