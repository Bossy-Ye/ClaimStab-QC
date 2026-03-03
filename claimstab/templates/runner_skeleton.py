"""Template: add a new execution backend runner.

Copy this file and adapt to your backend SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RunResult:
    score: float
    transpiled_depth: int | None = None
    transpiled_size: int | None = None


class MyRunner:
    """Runner contract expected by MatrixRunner backend interface."""

    def run_one(self, *, task, method, config, **kwargs) -> RunResult:
        """Execute one (task, method, perturbation config) point and return a score."""
        # 1) build executable object from task/method
        # 2) transpile/compile with config knobs
        # 3) execute
        # 4) task.evaluate(raw_result) -> float score
        raise NotImplementedError
