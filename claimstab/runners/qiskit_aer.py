# claimstab/runners/qiskit_aer.py
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable, Optional

from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator

from claimstab.devices.spec import DeviceProfile

try:
    # Qiskit Aer is a separate package in Qiskit 2.x
    from qiskit_aer import AerSimulator
except Exception as e:
    AerSimulator = None
    _AER_IMPORT_ERROR = e
else:
    _AER_IMPORT_ERROR = None

try:
    from qiskit_aer.noise import NoiseModel, depolarizing_error
except Exception:
    NoiseModel = None
    depolarizing_error = None


type Counts = dict[str, int]
type MetricFn = Callable[[Counts], float]

SAFE_BASIS = ["rz", "sx", "x", "cx"]

@dataclass(frozen=True, slots=True)
class AerRunConfig:
    """
    Configuration for a single Aer execution.

    All fields correspond to *software-visible perturbations*
    that are explicitly controlled in ClaimStab-QC.
    """
    shots: int = 1024
    optimization_level: int = 0          # {0,1,2,3}
    seed_transpiler: int | None = 0      # transpiler stochasticity
    seed_simulator: int | None = 0       # sampling stochasticity
    basis_gates: list[str] | None = None
    coupling_map: object | None = None
    layout_method: Optional[str] = None


@dataclass(frozen=True, slots=True)
class AerRunResult:
    """
    Minimal, claim-centric execution record.

    Counts are the *only semantic output*;
    circuit statistics are auxiliary diagnostics.
    """
    counts: Counts | None
    transpiled_depth: int
    transpiled_size: int
    two_qubit_count: int
    swap_count: int
    device_provider: str | None = None
    device_name: str | None = None
    device_mode: str | None = None
    device_snapshot_fingerprint: str | None = None
    device_snapshot_summary: dict[str, object] | None = None


class QiskitAerRunner:
    """
    Execution backend adapter with Aer/BasicSimulator backends.

    This class intentionally:
      - exposes perturbation knobs explicitly,
      - avoids deprecated APIs,
      - returns minimal but sufficient data for claim evaluation.

    It does NOT:
      - decide which perturbations to run,
      - aggregate results,
      - evaluate claims.

    Backend selection:
      - engine="aer": force AerSimulator
      - engine="basic": force BasicSimulator
      - engine="auto" (default): Aer if installed, otherwise BasicSimulator
      - CLAIMSTAB_SIMULATOR env var can set the default engine
    """

    def __init__(
        self,
        engine: str | None = None,
        *,
        spot_check_noise: bool = False,
        one_qubit_error: float = 0.001,
        two_qubit_error: float = 0.01,
    ) -> None:
        requested_engine = (engine or os.getenv("CLAIMSTAB_SIMULATOR", "auto")).lower()
        if requested_engine not in {"auto", "aer", "basic"}:
            raise ValueError(f"Unsupported engine '{requested_engine}'. Use one of: auto, aer, basic.")

        if requested_engine == "aer" and AerSimulator is None:
            raise ImportError(
                "qiskit-aer is not available. Install with:\n"
                "  pip install 'qiskit-aer~=0.17'\n\n"
                f"Original import error:\n{_AER_IMPORT_ERROR}"
            )
        if requested_engine == "auto":
            self.engine = "aer" if AerSimulator is not None else "basic"
        else:
            self.engine = requested_engine

        self.noise_model = None
        if spot_check_noise:
            if self.engine != "aer":
                raise ValueError("spot_check_noise requires Aer engine. Use --backend-engine aer or auto with qiskit-aer installed.")
            if NoiseModel is None or depolarizing_error is None:
                raise ImportError("qiskit-aer noise module is unavailable. Install qiskit-aer with noise support.")
            self.noise_model = self._build_spot_check_noise_model(
                one_qubit_error=one_qubit_error,
                two_qubit_error=two_qubit_error,
            )

    @staticmethod
    def _build_spot_check_noise_model(*, one_qubit_error: float, two_qubit_error: float):
        if one_qubit_error < 0.0 or two_qubit_error < 0.0:
            raise ValueError("Noise strengths must be non-negative.")
        noise_model = NoiseModel()
        noise_model.add_all_qubit_quantum_error(depolarizing_error(one_qubit_error, 1), ["rz", "sx", "x", "rx"])
        noise_model.add_all_qubit_quantum_error(depolarizing_error(two_qubit_error, 2), ["cx"])
        return noise_model

    @staticmethod
    def _transpiled_stats(transpiled: QuantumCircuit) -> tuple[int, int]:
        two_qubit_count = 0
        swap_count = 0
        for item in transpiled.data:
            op = getattr(item, "operation", None)
            qubits = getattr(item, "qubits", None)
            if op is None or qubits is None:
                # Backward compatibility with legacy tuple-like instruction records.
                op = item[0]
                qubits = item[1]
            op_name = str(getattr(op, "name", ""))
            if len(qubits) == 2:
                two_qubit_count += 1
            if op_name == "swap":
                swap_count += 1
        return two_qubit_count, swap_count

    def _transpile_with_profile(
        self,
        circuit: QuantumCircuit,
        cfg: AerRunConfig,
        *,
        backend,
        device_profile: DeviceProfile | None,
        device_backend,
    ) -> QuantumCircuit:
        if device_profile is not None and device_profile.enabled and device_backend is not None:
            return transpile(
                circuit,
                backend=device_backend,
                optimization_level=cfg.optimization_level,
                seed_transpiler=cfg.seed_transpiler,
                layout_method=cfg.layout_method,
            )

        if device_profile is not None and device_profile.enabled and device_profile.provider == "generic":
            return transpile(
                circuit,
                optimization_level=cfg.optimization_level,
                seed_transpiler=cfg.seed_transpiler,
                basis_gates=device_profile.basis_gates or cfg.basis_gates or SAFE_BASIS,
                coupling_map=device_profile.coupling_map or cfg.coupling_map,
                layout_method=cfg.layout_method,
            )

        if cfg.basis_gates is None and cfg.coupling_map is None:
            return transpile(
                circuit,
                backend=backend,
                optimization_level=cfg.optimization_level,
                seed_transpiler=cfg.seed_transpiler,
                layout_method=cfg.layout_method,
            )

        # When a custom coupling map is provided, force a safe 1Q/2Q basis
        # to avoid backend basis incompatibilities (e.g., 3Q gates like ccx).
        basis_gates = cfg.basis_gates if cfg.basis_gates is not None else SAFE_BASIS
        return transpile(
            circuit,
            optimization_level=cfg.optimization_level,
            seed_transpiler=cfg.seed_transpiler,
            basis_gates=basis_gates,
            coupling_map=cfg.coupling_map,
            layout_method=cfg.layout_method,
        )

    def run_counts(
        self,
        circuit: QuantumCircuit,
        cfg: AerRunConfig,
        *,
        device_profile: DeviceProfile | None = None,
        device_backend=None,
        noise_model_mode: str = "none",
        device_snapshot_fingerprint: str | None = None,
        device_snapshot_summary: dict[str, object] | None = None,
    ) -> AerRunResult:
        """
        Transpile and execute a circuit under a specific perturbation configuration.
        """
        profile = device_profile if device_profile is not None else DeviceProfile(enabled=False, provider="none")
        if profile.enabled and profile.mode == "transpile_only":
            transpiled = self._transpile_with_profile(
                circuit,
                cfg,
                backend=None,
                device_profile=profile,
                device_backend=device_backend,
            )
            counts: Counts | None = None
        else:
            if profile.enabled and profile.mode == "noisy_sim" and device_backend is not None:
                if self.engine != "aer":
                    raise ValueError("device_profile.mode=noisy_sim requires Aer engine.")
                if noise_model_mode == "from_device_profile":
                    backend = AerSimulator.from_backend(device_backend)
                else:
                    backend = AerSimulator(seed_simulator=cfg.seed_simulator)
                run_kwargs = {"shots": cfg.shots, "seed_simulator": cfg.seed_simulator}
                transpiled = self._transpile_with_profile(
                    circuit,
                    cfg,
                    backend=backend,
                    device_profile=profile,
                    device_backend=device_backend,
                )
            else:
                if self.engine == "aer":
                    backend = AerSimulator(seed_simulator=cfg.seed_simulator, noise_model=self.noise_model)
                    run_kwargs = {"shots": cfg.shots}
                else:
                    backend = BasicSimulator()
                    run_kwargs = {"shots": cfg.shots, "seed_simulator": cfg.seed_simulator}
                transpiled = self._transpile_with_profile(
                    circuit,
                    cfg,
                    backend=backend,
                    device_profile=profile if profile.enabled else None,
                    device_backend=device_backend,
                )

            job = backend.run(transpiled, **run_kwargs)
            result = job.result()
            raw_counts = result.get_counts()
            counts = {str(k): int(v) for k, v in dict(raw_counts).items()}

        two_qubit_count, swap_count = self._transpiled_stats(transpiled)

        return AerRunResult(
            counts=counts,
            transpiled_depth=transpiled.depth(),
            transpiled_size=transpiled.size(),
            two_qubit_count=two_qubit_count,
            swap_count=swap_count,
            device_provider=profile.provider if profile.enabled else None,
            device_name=profile.name if profile.enabled else None,
            device_mode=profile.mode if profile.enabled else None,
            device_snapshot_fingerprint=device_snapshot_fingerprint if profile.enabled else None,
            device_snapshot_summary=device_snapshot_summary if profile.enabled else None,
        )

    def run_metric(
            self,
            circuit: "QuantumCircuit",
            cfg: AerRunConfig,
            metric_fn: MetricFn,
            *,
            return_details: bool = False,
            device_profile: DeviceProfile | None = None,
            device_backend=None,
            noise_model_mode: str = "none",
            device_snapshot_fingerprint: str | None = None,
            device_snapshot_summary: dict[str, object] | None = None,
    ):
        """
        Run counts then compute a scalar metric from them.

        If return_details=True, returns a tuple:
            (score, AerRunResult)
        so you can inspect transpiled_depth/transpiled_size (sanity check that perturbations
        actually change the compiled circuit).
        """
        res = self.run_counts(
            circuit,
            cfg,
            device_profile=device_profile,
            device_backend=device_backend,
            noise_model_mode=noise_model_mode,
            device_snapshot_fingerprint=device_snapshot_fingerprint,
            device_snapshot_summary=device_snapshot_summary,
        )
        score = float(metric_fn(res.counts or {}))
        if return_details:
            return score, res
        return score
