from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any, Callable, Literal, Sequence

from claimstab.perturbations.space import PerturbationConfig, PerturbationSpace


SamplingMode = Literal["full_factorial", "random_k", "adaptive_ci"]


@dataclass(frozen=True)
class SamplingPolicy:
    mode: SamplingMode = "full_factorial"
    sample_size: int | None = None
    seed: int = 0
    target_ci_width: float | None = None
    max_sample_size: int | None = None
    min_sample_size: int = 8
    step_size: int = 8


@dataclass(frozen=True)
class AdaptiveSamplingResult:
    selected_configs: list[PerturbationConfig]
    evaluated_configs: int
    achieved_ci_width: float
    target_ci_width: float
    stop_reason: str


def normalize_repeats_to_seed_simulator(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Backward-compat adapter for legacy perturbation specs using `repeats`."""
    out = dict(raw)
    deprecated: list[str] = []
    repeats = out.get("repeats")
    if repeats is None or "seed_simulator" in out:
        return out, deprecated

    if isinstance(repeats, list):
        out["seed_simulator"] = [int(v) for v in repeats]
        deprecated.append("repeats")
        out.pop("repeats", None)
        return out, deprecated

    if isinstance(repeats, int):
        if repeats > 0:
            out["seed_simulator"] = list(range(repeats))
            deprecated.append("repeats")
        out.pop("repeats", None)
        return out, deprecated

    return out, deprecated



def sample_configs(space: PerturbationSpace, policy: SamplingPolicy) -> list[PerturbationConfig]:
    configs = list(space.iter_configs())
    if policy.mode == "full_factorial":
        return configs

    if policy.mode == "random_k":
        if policy.sample_size is None or policy.sample_size <= 0:
            raise ValueError("sample_size must be a positive integer for mode='random_k'")
        k = min(policy.sample_size, len(configs))
        return Random(policy.seed).sample(configs, k)

    if policy.mode == "adaptive_ci":
        max_size = policy.max_sample_size if policy.max_sample_size is not None else policy.sample_size
        if max_size is None or max_size <= 0:
            raise ValueError("max_sample_size (or sample_size) must be positive for mode='adaptive_ci'")
        k = min(max_size, len(configs))
        return Random(policy.seed).sample(configs, k)

    raise ValueError(f"Unsupported sampling mode: {policy.mode}")



def ensure_config_included(
    configs: list[PerturbationConfig],
    target: PerturbationConfig,
) -> list[PerturbationConfig]:
    if target in configs:
        return configs
    return [target, *configs]


def adaptive_sample_configs(
    ordered_configs: Sequence[PerturbationConfig],
    *,
    evaluate_prefix: Callable[[list[PerturbationConfig]], Any],
    target_ci_width: float,
    min_sample_size: int = 8,
    step_size: int = 8,
    max_sample_size: int | None = None,
) -> AdaptiveSamplingResult:
    if target_ci_width <= 0.0:
        raise ValueError("target_ci_width must be > 0")
    if min_sample_size <= 0:
        raise ValueError("min_sample_size must be > 0")
    if step_size <= 0:
        raise ValueError("step_size must be > 0")

    configs = list(ordered_configs)
    if not configs:
        raise ValueError("ordered_configs cannot be empty")

    hard_max = len(configs) if max_sample_size is None else min(len(configs), max_sample_size)
    if hard_max <= 0:
        raise ValueError("max_sample_size must be > 0")

    n = min(max(min_sample_size, 1), hard_max)
    best_n = n
    best_w = 1.0
    stop_reason = "max_budget_reached"

    while True:
        prefix = configs[:n]
        estimate = evaluate_prefix(prefix)
        if isinstance(estimate, tuple) and len(estimate) >= 2:
            low, high = float(estimate[0]), float(estimate[1])
            width = max(0.0, high - low)
        elif hasattr(estimate, "ci_low") and hasattr(estimate, "ci_high"):
            width = max(0.0, float(getattr(estimate, "ci_high")) - float(getattr(estimate, "ci_low")))
        else:
            raise TypeError("evaluate_prefix must return (ci_low, ci_high) or an object with ci_low/ci_high")
        best_n = n
        best_w = width
        if width <= target_ci_width:
            stop_reason = "target_ci_width_reached"
            break
        if n >= hard_max:
            break
        n = min(hard_max, n + step_size)

    return AdaptiveSamplingResult(
        selected_configs=configs[:best_n],
        evaluated_configs=best_n,
        achieved_ci_width=best_w,
        target_ci_width=target_ci_width,
        stop_reason=stop_reason,
    )
