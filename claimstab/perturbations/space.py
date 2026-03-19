from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class PerturbationLevel(str, Enum):
    """
    We keep 4 levels explicit: L1, L2, L3, L4.
    """
    COMPILATION = "compilation"   # transpiler / compilation heuristics
    EXECUTION = "execution"       # sampling uncertainty (shots / sim seed / repetitions)
    HYBRID_OPT = "hybrid_opt"     # classical optimizer randomness (init seed)
    BACKEND = "backend"           # time-window / calibration (spot-check)


# -------------------------
# Level 1 (L1): Compilation-level
# -------------------------
@dataclass(frozen=True)
class CompilationPerturbation:
    """
    Compilation-level knobs that are software-visible and controllable in Qiskit.
    """
    seed_transpiler: int
    optimization_level: int
    layout_method: str  # "trivial" or "sabre"

# -------------------------
# Level 2 (L2): Execution-level
# -------------------------
@dataclass(frozen=True)
class ExecutionPerturbation:
    shots: int
    seed_simulator: int


# -------------------------
# Level 3 (L3): Hybrid-optimization-level
# -------------------------
@dataclass(frozen=True)
class HybridOptimizationPerturbation:
    """
    Optional hybrid optimization knobs for tasks that support them (e.g., MaxCut/QAOA).

    These are intentionally orthogonal to compilation/execution knobs.
    """

    init_strategy: str  # "fixed" | "random"
    init_seed: int


# -------------------------
# Unified config (a single run)
# -------------------------
@dataclass(frozen=True)
class PerturbationConfig:
    """
    A single software-visible perturbation configuration.
    """
    compilation: CompilationPerturbation
    execution: ExecutionPerturbation
    hybrid_opt: HybridOptimizationPerturbation | None = None


@dataclass(frozen=True)
class PerturbationSpace:
    seeds_transpiler: List[int]
    opt_levels: List[int]
    layout_methods: List[str]

    shots_list: List[int]
    seeds_simulator: List[int]
    hybrid_init_strategies: List[str] | None = None
    hybrid_init_seeds: List[int] | None = None

    def iter_configs(self) -> Iterable[PerturbationConfig]:
        hybrid_strategies = self.hybrid_init_strategies if self.hybrid_init_strategies else [None]
        hybrid_seeds = self.hybrid_init_seeds if self.hybrid_init_seeds else [None]
        for st in self.seeds_transpiler:
            for o in self.opt_levels:
                for l in self.layout_methods:
                    for shots in self.shots_list:
                        for ss in self.seeds_simulator:
                            for init_strategy in hybrid_strategies:
                                for init_seed in hybrid_seeds:
                                    hybrid_opt = None
                                    if init_strategy is not None and init_seed is not None:
                                        hybrid_opt = HybridOptimizationPerturbation(
                                            init_strategy=str(init_strategy),
                                            init_seed=int(init_seed),
                                        )
                                    yield PerturbationConfig(
                                        compilation=CompilationPerturbation(
                                            seed_transpiler=st,
                                            optimization_level=o,
                                            layout_method=l,
                                        ),
                                        execution=ExecutionPerturbation(
                                            shots=shots,
                                            seed_simulator=ss,
                                        ),
                                        hybrid_opt=hybrid_opt,
                                    )

    def with_hybrid_optimization(
        self,
        *,
        init_strategies: list[str],
        init_seeds: list[int],
    ) -> "PerturbationSpace":
        return PerturbationSpace(
            seeds_transpiler=list(self.seeds_transpiler),
            opt_levels=list(self.opt_levels),
            layout_methods=list(self.layout_methods),
            shots_list=list(self.shots_list),
            seeds_simulator=list(self.seeds_simulator),
            hybrid_init_strategies=[str(v) for v in init_strategies],
            hybrid_init_seeds=[int(v) for v in init_seeds],
        )

    def has_hybrid_axis(self) -> bool:
        return bool(self.hybrid_init_strategies and self.hybrid_init_seeds)

    def hybrid_axis_size(self) -> int:
        if not self.has_hybrid_axis():
            return 1
        return len(self.hybrid_init_strategies or []) * len(self.hybrid_init_seeds or [])

    def _core_size(self) -> int:
        return (
            len(self.seeds_transpiler)
            * len(self.opt_levels)
            * len(self.layout_methods)
            * len(self.shots_list)
            * len(self.seeds_simulator)
        )

    def size(self) -> int:
        return self._core_size() * self.hybrid_axis_size()

    @staticmethod
    def conf_level_default() -> "PerturbationSpace":
        return PerturbationSpace(
            seeds_transpiler=list(range(10)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[1024],
            seeds_simulator=[0],
        )

    @staticmethod
    def day1_default() -> "PerturbationSpace":
        """
        Backward-compatible alias for demos and docs.
        """
        return PerturbationSpace.conf_level_default()

    @staticmethod
    def compilation_only() -> "PerturbationSpace":
        return PerturbationSpace(
            seeds_transpiler=list(range(10)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[1024],  # FIXED
            seeds_simulator=[0],  # FIXED
        )

    @staticmethod
    def sampling_only() -> "PerturbationSpace":
        """
        Execution-focused stress space.

        Includes low-shot values (16/32/64) to intentionally stress sampling
        uncertainty, model common exploratory low-budget runs, and expose
        claim failure modes that disappear at high shots.
        """
        return PerturbationSpace(
            seeds_transpiler=[0],  # FIXED compiler randomness
            opt_levels=[1],  # FIXED
            layout_methods=["sabre"],  # FIXED
            shots_list=[16, 32, 64, 256, 1024],
            seeds_simulator=list(range(20)),
        )

    @staticmethod
    def combined_light() -> "PerturbationSpace":
        return PerturbationSpace(
            seeds_transpiler=list(range(10)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[64],
            seeds_simulator=[0, 1, 2],
        )

    @staticmethod
    def compilation_only_exact() -> "PerturbationSpace":
        """
        Small exact compilation grid used by the evaluation_v2 rerun scaffold.

        Size = 3 transpiler seeds x 3 optimization levels x 3 layout methods = 27.
        """
        return PerturbationSpace(
            seeds_transpiler=[0, 1, 2],
            opt_levels=[0, 1, 2],
            layout_methods=["trivial", "dense", "sabre"],
            shots_list=[1024],
            seeds_simulator=[0],
        )

    @staticmethod
    def sampling_only_exact() -> "PerturbationSpace":
        """
        Small exact execution grid used by the evaluation_v2 rerun scaffold.

        Size = 4 shot values x 5 simulator seeds = 20.
        """
        return PerturbationSpace(
            seeds_transpiler=[0],
            opt_levels=[1],
            layout_methods=["sabre"],
            shots_list=[16, 64, 256, 1024],
            seeds_simulator=[0, 1, 2, 3, 4],
        )

    @staticmethod
    def combined_light_exact() -> "PerturbationSpace":
        """
        Small mixed grid used by the evaluation_v2 rerun scaffold.

        Size = 3 transpiler seeds x 2 layouts x 5 simulator seeds = 30.
        """
        return PerturbationSpace(
            seeds_transpiler=[0, 1, 2],
            opt_levels=[1],
            layout_methods=["trivial", "sabre"],
            shots_list=[64],
            seeds_simulator=[0, 1, 2, 3, 4],
        )

    @staticmethod
    def compilation_stress() -> "PerturbationSpace":
        """
        Optional expanded compilation-focused preset.
        """
        return PerturbationSpace(
            seeds_transpiler=list(range(20)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[1024],
            seeds_simulator=[0],
        )

    @staticmethod
    def sampling_stress() -> "PerturbationSpace":
        """
        Optional expanded execution-focused preset with wider shot/seed ranges.
        """
        return PerturbationSpace(
            seeds_transpiler=[0],
            opt_levels=[1],
            layout_methods=["sabre"],
            shots_list=[8, 16, 32, 64, 128, 256, 1024, 4096],
            seeds_simulator=list(range(32)),
        )

    @staticmethod
    def sampling_policy_eval() -> "PerturbationSpace":
        """
        E5-only expanded execution grid for policy-comparison studies.

        Size = 9 shot values x 55 simulator seeds = 495.
        """
        return PerturbationSpace(
            seeds_transpiler=[0],
            opt_levels=[1],
            layout_methods=["sabre"],
            shots_list=[8, 16, 32, 64, 128, 256, 512, 1024, 2048],
            seeds_simulator=list(range(55)),
        )

    @staticmethod
    def combined_stress() -> "PerturbationSpace":
        """
        Optional mixed preset for stronger stress testing across both dimensions.
        """
        return PerturbationSpace(
            seeds_transpiler=list(range(12)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[16, 64, 256, 1024],
            seeds_simulator=[0, 1, 2, 3, 4],
        )

    def iter_configs_with_operators(self) -> Iterable[PerturbationConfig]:
        """
        Optional operator-shim path (backward-compatible).
        Default callers still use iter_configs().
        """
        from claimstab.perturbations.operators import iter_space_configs_via_operators

        yield from iter_space_configs_via_operators(self)
