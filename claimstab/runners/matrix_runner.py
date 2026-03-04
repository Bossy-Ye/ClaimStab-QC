# claimstab/runners/matrix_runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from qiskit.transpiler import CouplingMap

from claimstab.devices.spec import DeviceProfile
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import PerturbationConfig, PerturbationSpace
from claimstab.runners.qiskit_aer import AerRunConfig, QiskitAerRunner


@dataclass(frozen=True, slots=True)
class ScoreRow:
    """
    One row in the experiment matrix (paper-facing).
    """

    instance_id: str
    seed_transpiler: int
    optimization_level: int
    transpiled_depth: int
    transpiled_size: int
    method: str
    score: float
    metric_name: str = "objective"
    seed_simulator: int | None = None
    shots: int = 1024
    layout_method: str | None = None
    device_provider: str | None = None
    device_name: str | None = None
    device_mode: str | None = None
    device_snapshot_fingerprint: str | None = None
    circuit_depth: int | None = None
    two_qubit_count: int | None = None
    swap_count: int | None = None
    counts: dict[str, int] | None = None


class MatrixRunner:
    """
    Top-conference level matrix runner.

    Orchestrates:
        methods × perturbation space

    Claim-agnostic:
      - produces a clean score matrix
      - claim evaluation happens elsewhere
    """

    def __init__(self, backend: QiskitAerRunner | None = None) -> None:
        self.backend = backend or QiskitAerRunner()

    def run(
        self,
        task: Any,
        methods: List[MethodSpec],
        space: PerturbationSpace,
        configs: List[PerturbationConfig] | None = None,
        *,
        coupling_map: CouplingMap | list[list[int]] | None,
        metric_name: str = "objective",
        device_profile: DeviceProfile | None = None,
        device_backend=None,
        noise_model_mode: str = "none",
        device_snapshot_fingerprint: str | None = None,
        device_snapshot_summary: dict[str, object] | None = None,
        store_counts: bool = False,
    ) -> List[ScoreRow]:
        """
        task contract:
          task.build(method: MethodSpec)
            -> (QuantumCircuit, metric_fn)
        """
        rows: List[ScoreRow] = []
        run_configs = configs if configs is not None else list(space.iter_configs())

        for method in methods:
            circuit, metric_fn = task.build(method)

            for pc in run_configs:
                comp = pc.compilation
                exe = pc.execution
                aer_cfg = AerRunConfig(
                    shots=exe.shots,
                    seed_simulator=exe.seed_simulator,
                    optimization_level=comp.optimization_level,
                    seed_transpiler=comp.seed_transpiler,
                    layout_method=comp.layout_method,
                    coupling_map=coupling_map,
                )

                score, details = self.backend.run_metric(
                    circuit,
                    aer_cfg,
                    metric_fn,
                    return_details=True,
                    device_profile=device_profile,
                    device_backend=device_backend,
                    noise_model_mode=noise_model_mode,
                    device_snapshot_fingerprint=device_snapshot_fingerprint,
                    device_snapshot_summary=device_snapshot_summary,
                )

                if metric_name == "objective":
                    effective_score = score
                elif metric_name == "circuit_depth":
                    effective_score = float(details.transpiled_depth)
                elif metric_name == "two_qubit_count":
                    effective_score = float(details.two_qubit_count)
                elif metric_name == "swap_count":
                    effective_score = float(details.swap_count)
                else:
                    raise ValueError(
                        f"Unsupported metric_name '{metric_name}'. "
                        "Use one of: objective, circuit_depth, two_qubit_count, swap_count."
                    )

                rows.append(
                    ScoreRow(
                        instance_id=getattr(task, "instance_id", "unknown"),
                        seed_transpiler=comp.seed_transpiler,
                        optimization_level=comp.optimization_level,
                        transpiled_depth=details.transpiled_depth,
                        transpiled_size=details.transpiled_size,
                        method=method.name,
                        metric_name=metric_name,
                        score=effective_score,
                        layout_method=comp.layout_method,
                        seed_simulator=exe.seed_simulator,
                        shots=exe.shots,
                        device_provider=details.device_provider,
                        device_name=details.device_name,
                        device_mode=details.device_mode,
                        device_snapshot_fingerprint=details.device_snapshot_fingerprint,
                        circuit_depth=details.transpiled_depth,
                        two_qubit_count=details.two_qubit_count,
                        swap_count=details.swap_count,
                        counts=details.counts if store_counts else None,
                    )
                )

        return rows
