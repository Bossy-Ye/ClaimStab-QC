# claimstab/runners/qiskit_aer.py
from __future__ import annotations

from dataclasses import dataclass
import os
from time import perf_counter
from typing import Any, Callable, Optional

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
    transpile_time_ms: float | None = None
    execute_time_ms: float | None = None
    wall_time_ms: float | None = None


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
        cache_transpilation: bool = True,
        cache_backends: bool = True,
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

        self.cache_transpilation = bool(cache_transpilation)
        self.cache_backends = bool(cache_backends)
        self._transpile_cache: dict[tuple[object, ...], QuantumCircuit] = {}
        self._backend_cache: dict[tuple[object, ...], object] = {}

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

    @staticmethod
    def _backend_identity(backend: object | None) -> tuple[str, str | None, int | None]:
        if backend is None:
            return ("none", None, None)
        backend_type = f"{type(backend).__module__}.{type(backend).__qualname__}"
        backend_name: str | None = None
        for attr in ("name", "backend_name"):
            value = getattr(backend, attr, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
            if value is not None:
                backend_name = str(value)
                break
        num_qubits_raw = getattr(backend, "num_qubits", None)
        try:
            num_qubits = int(num_qubits_raw) if num_qubits_raw is not None else None
        except Exception:
            num_qubits = None
        return (backend_type, backend_name, num_qubits)

    @staticmethod
    def _coupling_map_fingerprint(coupling_map: object | None) -> object | None:
        if coupling_map is None:
            return None
        edges: object | None = None
        get_edges = getattr(coupling_map, "get_edges", None)
        if callable(get_edges):
            try:
                edges = get_edges()
            except Exception:
                edges = None
        elif isinstance(coupling_map, (list, tuple)):
            edges = coupling_map

        if edges is not None:
            normalized_edges: list[tuple[str, str]] = []
            try:
                for edge in edges:
                    if isinstance(edge, (list, tuple)) and len(edge) == 2:
                        normalized_edges.append((str(edge[0]), str(edge[1])))
                if normalized_edges:
                    return tuple(sorted(normalized_edges))
            except Exception:
                pass
        return repr(coupling_map)

    def _transpile_cache_key(
        self,
        circuit: QuantumCircuit,
        cfg: AerRunConfig,
        *,
        backend,
        device_profile: DeviceProfile | None,
        device_backend,
    ) -> tuple[object, ...] | None:
        if not self.cache_transpilation:
            return None
        # Do not cache when transpiler seed is intentionally unset, preserving
        # stochastic transpilation behavior for repeated calls.
        if cfg.seed_transpiler is None:
            return None

        profile_enabled = bool(device_profile is not None and device_profile.enabled)
        target_backend = device_backend if profile_enabled and device_backend is not None else backend
        op_counts = tuple(
            sorted((str(op_name), int(op_count)) for op_name, op_count in dict(circuit.count_ops()).items())
        )
        return (
            id(circuit),
            int(getattr(circuit, "num_qubits", 0)),
            int(getattr(circuit, "num_clbits", 0)),
            int(circuit.size()),
            int(circuit.depth()),
            op_counts,
            int(cfg.optimization_level),
            int(cfg.seed_transpiler),
            cfg.layout_method,
            tuple(cfg.basis_gates) if cfg.basis_gates is not None else None,
            self._coupling_map_fingerprint(cfg.coupling_map),
            profile_enabled,
            getattr(device_profile, "provider", None) if profile_enabled else None,
            getattr(device_profile, "name", None) if profile_enabled else None,
            getattr(device_profile, "mode", None) if profile_enabled else None,
            self._backend_identity(target_backend),
        )

    def _get_cached_backend(self, key: tuple[object, ...], factory: Callable[[], object]) -> object:
        if not self.cache_backends:
            return factory()
        cached = self._backend_cache.get(key)
        if cached is not None:
            return cached
        created = factory()
        self._backend_cache[key] = created
        return created

    def _resolve_backend_and_run_kwargs(
        self,
        cfg: AerRunConfig,
        *,
        profile: DeviceProfile,
        device_backend,
        noise_model_mode: str,
    ) -> tuple[object, dict[str, Any]]:
        if profile.enabled and profile.mode == "noisy_sim" and device_backend is not None:
            if self.engine != "aer":
                raise ValueError("device_profile.mode=noisy_sim requires Aer engine.")
            if noise_model_mode == "from_device_profile":
                backend = self._get_cached_backend(
                    ("aer_from_backend", self._backend_identity(device_backend)),
                    lambda: AerSimulator.from_backend(device_backend),
                )
            else:
                backend = self._get_cached_backend(
                    ("aer_noisy_sim", cfg.seed_simulator, id(self.noise_model)),
                    lambda: AerSimulator(seed_simulator=cfg.seed_simulator),
                )
            run_kwargs = {"shots": cfg.shots, "seed_simulator": cfg.seed_simulator}
            return backend, run_kwargs

        if self.engine == "aer":
            backend = self._get_cached_backend(
                ("aer_default", cfg.seed_simulator, id(self.noise_model)),
                lambda: AerSimulator(seed_simulator=cfg.seed_simulator, noise_model=self.noise_model),
            )
            run_kwargs = {"shots": cfg.shots}
            return backend, run_kwargs

        backend = self._get_cached_backend(("basic_default",), BasicSimulator)
        run_kwargs = {"shots": cfg.shots, "seed_simulator": cfg.seed_simulator}
        return backend, run_kwargs

    def _get_transpiled_circuit(
        self,
        circuit: QuantumCircuit,
        cfg: AerRunConfig,
        *,
        backend,
        device_profile: DeviceProfile | None,
        device_backend,
    ) -> QuantumCircuit:
        key = self._transpile_cache_key(
            circuit,
            cfg,
            backend=backend,
            device_profile=device_profile,
            device_backend=device_backend,
        )
        if key is None:
            return self._transpile_with_profile(
                circuit,
                cfg,
                backend=backend,
                device_profile=device_profile,
                device_backend=device_backend,
            )

        cached = self._transpile_cache.get(key)
        if cached is not None:
            return cached

        transpiled = self._transpile_with_profile(
            circuit,
            cfg,
            backend=backend,
            device_profile=device_profile,
            device_backend=device_backend,
        )
        self._transpile_cache[key] = transpiled
        return transpiled

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
        wall_t0 = perf_counter()
        profile = device_profile if device_profile is not None else DeviceProfile(enabled=False, provider="none")
        transpile_time_ms: float = 0.0
        execute_time_ms: float = 0.0
        if profile.enabled and profile.mode == "transpile_only":
            transpile_t0 = perf_counter()
            transpiled = self._get_transpiled_circuit(
                circuit,
                cfg,
                backend=None,
                device_profile=profile,
                device_backend=device_backend,
            )
            transpile_time_ms = (perf_counter() - transpile_t0) * 1000.0
            counts: Counts | None = None
        else:
            backend, run_kwargs = self._resolve_backend_and_run_kwargs(
                cfg,
                profile=profile,
                device_backend=device_backend,
                noise_model_mode=noise_model_mode,
            )
            transpile_t0 = perf_counter()
            transpiled = self._get_transpiled_circuit(
                circuit,
                cfg,
                backend=backend,
                device_profile=profile if profile.enabled else None,
                device_backend=device_backend,
            )
            transpile_time_ms = (perf_counter() - transpile_t0) * 1000.0
            execute_t0 = perf_counter()
            job = backend.run(transpiled, **run_kwargs)
            result = job.result()
            raw_counts = result.get_counts()
            counts = {str(k): int(v) for k, v in dict(raw_counts).items()}
            execute_time_ms = (perf_counter() - execute_t0) * 1000.0

        two_qubit_count, swap_count = self._transpiled_stats(transpiled)
        wall_time_ms = (perf_counter() - wall_t0) * 1000.0

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
            transpile_time_ms=transpile_time_ms,
            execute_time_ms=execute_time_ms,
            wall_time_ms=wall_time_ms,
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
