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
# Unified config (a single run)
# -------------------------
@dataclass(frozen=True)
class PerturbationConfig:
    """
    A single software-visible perturbation configuration.
    """
    compilation: CompilationPerturbation
    execution: ExecutionPerturbation


@dataclass(frozen=True)
class PerturbationSpace:
    seeds_transpiler: List[int]
    opt_levels: List[int]
    layout_methods: List[str]

    shots_list: List[int]
    seeds_simulator: List[int]

    def iter_configs(self) -> Iterable[PerturbationConfig]:
        for st in self.seeds_transpiler:
            for o in self.opt_levels:
                for l in self.layout_methods:
                    for shots in self.shots_list:
                        for ss in self.seeds_simulator:
                            yield PerturbationConfig(
                                compilation=CompilationPerturbation(
                                    seed_transpiler=st,
                                    optimization_level=o,
                                    layout_method=l,
                                ),
                                execution=ExecutionPerturbation(
                                    shots=shots,
                                    seed_simulator=ss,
                                )
                            )

    def iter_configs_with_operators(self) -> Iterable[PerturbationConfig]:
        """
        Optional operator-shim path (backward-compatible).
        Default callers still use iter_configs().
        """
        from claimstab.perturbations.operators import iter_space_configs_via_operators

        yield from iter_space_configs_via_operators(self)

    def size(self) -> int:
        return (
            len(self.seeds_transpiler)
            * len(self.opt_levels)
            * len(self.layout_methods)
            * len(self.shots_list)
            * len(self.seeds_simulator)
        )

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
