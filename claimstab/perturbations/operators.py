from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Protocol

from claimstab.perturbations.space import (
    CompilationPerturbation,
    ExecutionPerturbation,
    HybridOptimizationPerturbation,
    PerturbationConfig,
    PerturbationSpace,
)


class PerturbationOperator(Protocol):
    """Minimal operator shim: apply a single perturbation change to a base config."""

    name: str

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        ...


@dataclass(frozen=True)
class SeedTranspilerOperator:
    value: int
    name: str = "seed_transpiler"

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=CompilationPerturbation(
                seed_transpiler=int(self.value),
                optimization_level=base_config.compilation.optimization_level,
                layout_method=base_config.compilation.layout_method,
            ),
            execution=base_config.execution,
            hybrid_opt=base_config.hybrid_opt,
        )


@dataclass(frozen=True)
class OptimizationLevelOperator:
    value: int
    name: str = "optimization_level"

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=CompilationPerturbation(
                seed_transpiler=base_config.compilation.seed_transpiler,
                optimization_level=int(self.value),
                layout_method=base_config.compilation.layout_method,
            ),
            execution=base_config.execution,
            hybrid_opt=base_config.hybrid_opt,
        )


@dataclass(frozen=True)
class LayoutMethodOperator:
    value: str
    name: str = "layout_method"

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=CompilationPerturbation(
                seed_transpiler=base_config.compilation.seed_transpiler,
                optimization_level=base_config.compilation.optimization_level,
                layout_method=str(self.value),
            ),
            execution=base_config.execution,
            hybrid_opt=base_config.hybrid_opt,
        )


@dataclass(frozen=True)
class ShotsOperator:
    value: int
    name: str = "shots"

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=base_config.compilation,
            execution=ExecutionPerturbation(
                shots=int(self.value),
                seed_simulator=base_config.execution.seed_simulator,
            ),
            hybrid_opt=base_config.hybrid_opt,
        )


@dataclass(frozen=True)
class SeedSimulatorOperator:
    value: int
    name: str = "seed_simulator"

    def apply(self, base_config: PerturbationConfig) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=base_config.compilation,
            execution=ExecutionPerturbation(
                shots=base_config.execution.shots,
                seed_simulator=int(self.value),
            ),
            hybrid_opt=base_config.hybrid_opt,
        )


def base_config_for_space(space: PerturbationSpace) -> PerturbationConfig:
    hybrid_opt = None
    if space.hybrid_init_strategies and space.hybrid_init_seeds:
        hybrid_opt = HybridOptimizationPerturbation(
            init_strategy=str(space.hybrid_init_strategies[0]),
            init_seed=int(space.hybrid_init_seeds[0]),
        )
    return PerturbationConfig(
        compilation=CompilationPerturbation(
            seed_transpiler=int(space.seeds_transpiler[0]),
            optimization_level=int(space.opt_levels[0]),
            layout_method=str(space.layout_methods[0]),
        ),
        execution=ExecutionPerturbation(
            shots=int(space.shots_list[0]),
            seed_simulator=int(space.seeds_simulator[0]),
        ),
        hybrid_opt=hybrid_opt,
    )


def iter_space_configs_via_operators(space: PerturbationSpace) -> Iterable[PerturbationConfig]:
    """
    Operator-shim path for perturbation generation.

    This intentionally mirrors the existing Cartesian ordering and values:
    seed_transpiler -> optimization_level -> layout_method -> shots -> seed_simulator.
    """
    base = base_config_for_space(space)
    hybrid_strategies = list(space.hybrid_init_strategies or [None])
    hybrid_seeds = list(space.hybrid_init_seeds or [None])
    for st, opt, layout, shots, seed_sim, init_strategy, init_seed in product(
        space.seeds_transpiler,
        space.opt_levels,
        space.layout_methods,
        space.shots_list,
        space.seeds_simulator,
        hybrid_strategies,
        hybrid_seeds,
    ):
        cfg = base
        cfg = PerturbationConfig(
            compilation=cfg.compilation,
            execution=cfg.execution,
            hybrid_opt=(
                None
                if init_strategy is None or init_seed is None
                else HybridOptimizationPerturbation(
                    init_strategy=str(init_strategy),
                    init_seed=int(init_seed),
                )
            ),
        )
        for op in (
            SeedTranspilerOperator(st),
            OptimizationLevelOperator(opt),
            LayoutMethodOperator(layout),
            ShotsOperator(shots),
            SeedSimulatorOperator(seed_sim),
        ):
            cfg = op.apply(cfg)
        yield cfg
