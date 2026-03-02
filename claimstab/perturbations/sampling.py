from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Literal

from claimstab.perturbations.space import PerturbationConfig, PerturbationSpace


SamplingMode = Literal["full_factorial", "random_k"]


@dataclass(frozen=True)
class SamplingPolicy:
    mode: SamplingMode = "full_factorial"
    sample_size: int | None = None
    seed: int = 0



def sample_configs(space: PerturbationSpace, policy: SamplingPolicy) -> list[PerturbationConfig]:
    configs = list(space.iter_configs())
    if policy.mode == "full_factorial":
        return configs

    if policy.mode == "random_k":
        if policy.sample_size is None or policy.sample_size <= 0:
            raise ValueError("sample_size must be a positive integer for mode='random_k'")
        k = min(policy.sample_size, len(configs))
        return Random(policy.seed).sample(configs, k)

    raise ValueError(f"Unsupported sampling mode: {policy.mode}")



def ensure_config_included(
    configs: list[PerturbationConfig],
    target: PerturbationConfig,
) -> list[PerturbationConfig]:
    if target in configs:
        return configs
    return [target, *configs]
