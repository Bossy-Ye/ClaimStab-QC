from __future__ import annotations

from dataclasses import dataclass
import os
from time import perf_counter
from typing import Any, Callable

from qiskit import QuantumCircuit, transpile

from claimstab.devices.backend_snapshot import fingerprint, snapshot_from_backend
from claimstab.devices.spec import DeviceProfile


type Counts = dict[str, int]
type MetricFn = Callable[[Counts], float]

_FACADE_BACKENDS = (
    "facade_adonis",
    "facade_apollo",
    "facade_aphrodite",
    "facade_deneb",
    "facade_garnet",
)


def _is_facade_backend_name(name: str | None) -> bool:
    return bool(name and name in _FACADE_BACKENDS)


def _is_mock_quantum_computer(name: str | None) -> bool:
    return bool(name and str(name).endswith(":mock"))


@dataclass(frozen=True, slots=True)
class IQMRunResult:
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


def _load_iqm_provider_type():
    try:
        from iqm.qiskit_iqm import IQMProvider
    except Exception as exc:  # pragma: no cover - import path depends on optional dep
        raise ImportError(
            "IQM hardware support requires iqm-client with Qiskit extras. Install with:\n"
            "  pip install 'claimstab-qc[iqm]'"
        ) from exc
    return IQMProvider


class QiskitIQMRunner:
    """Minimal IQM/VTT hardware runner for small ClaimStab slices."""

    def __init__(
        self,
        engine: str | None = None,
        *,
        server_url: str | None = None,
        quantum_computer: str | None = None,
        backend_name: str | None = None,
        token: str | None = None,
        token_env: str = "IQM_TOKEN",
        calibration_set_id: str | None = None,
        cache_transpilation: bool = True,
        **_: Any,
    ) -> None:
        del engine  # kept for drop-in compatibility with the Aer runner constructor
        self.server_url = server_url or os.getenv("CLAIMSTAB_IQM_SERVER_URL")
        self.quantum_computer = quantum_computer or os.getenv("CLAIMSTAB_IQM_QUANTUM_COMPUTER")
        self.backend_name = backend_name or os.getenv("CLAIMSTAB_IQM_BACKEND")
        self.token = token if token is not None else os.getenv(token_env)
        self.calibration_set_id = calibration_set_id or os.getenv("CLAIMSTAB_IQM_CALIBRATION_SET_ID")
        self.cache_transpilation = bool(cache_transpilation)
        self._transpile_cache: dict[tuple[object, ...], QuantumCircuit] = {}

        if not self.server_url:
            raise ValueError(
                "IQM hardware execution requires a server URL. "
                "Set CLAIMSTAB_IQM_SERVER_URL or pass server_url explicitly."
            )
        if not self.quantum_computer:
            raise ValueError(
                "IQM hardware execution requires a quantum computer name. "
                "Set CLAIMSTAB_IQM_QUANTUM_COMPUTER or pass quantum_computer explicitly."
            )
        if _is_facade_backend_name(self.backend_name) and not _is_mock_quantum_computer(self.quantum_computer):
            raise ValueError(
                "IQM facade backends must be used with a mock quantum computer name ending in ':mock'. "
                "Using a facade backend against a real quantum computer can waste credits and time."
            )

        provider_cls = _load_iqm_provider_type()
        provider_kwargs: dict[str, Any] = {"quantum_computer": self.quantum_computer}
        if self.token:
            provider_kwargs["token"] = self.token
        self.provider = provider_cls(self.server_url, **provider_kwargs)

        backend_kwargs: dict[str, Any] = {}
        if self.calibration_set_id:
            backend_kwargs["calibration_set_id"] = self.calibration_set_id

        if self.backend_name:
            self.backend = self.provider.get_backend(self.backend_name, **backend_kwargs)
        else:
            self.backend = self.provider.get_backend(**backend_kwargs)

        try:
            snap = snapshot_from_backend(self.backend)
        except Exception:
            backend_name_attr = getattr(self.backend, "name", None)
            backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
            snap = {
                "backend_name": str(backend_name_value or self.backend_name or self.quantum_computer),
                "backend_class": type(self.backend).__name__,
                "num_qubits": int(getattr(self.backend, "num_qubits", 0) or 0),
            }
        self.snapshot = snap
        self.snapshot_fingerprint = fingerprint(snap)
        if _is_facade_backend_name(self.backend_name):
            self.device_mode = "facade"
        elif _is_mock_quantum_computer(self.quantum_computer):
            self.device_mode = "mock_hardware"
        else:
            self.device_mode = "hardware"

    @classmethod
    def available_backends(
        cls,
        *,
        server_url: str | None = None,
        quantum_computer: str | None = None,
        token: str | None = None,
        token_env: str = "IQM_TOKEN",
        calibration_set_id: str | None = None,
        include_facades: bool = True,
    ) -> list[dict[str, Any]]:
        resolved_server_url = server_url or os.getenv("CLAIMSTAB_IQM_SERVER_URL")
        resolved_quantum_computer = quantum_computer or os.getenv("CLAIMSTAB_IQM_QUANTUM_COMPUTER")
        if not resolved_server_url or not resolved_quantum_computer:
            raise ValueError(
                "Listing IQM backends requires both server_url and quantum_computer. "
                "Set CLAIMSTAB_IQM_SERVER_URL / CLAIMSTAB_IQM_QUANTUM_COMPUTER or pass them explicitly."
            )

        provider_cls = _load_iqm_provider_type()
        provider_kwargs: dict[str, Any] = {"quantum_computer": resolved_quantum_computer}
        resolved_token = token if token is not None else os.getenv(token_env)
        if resolved_token:
            provider_kwargs["token"] = resolved_token
        provider = provider_cls(resolved_server_url, **provider_kwargs)

        backend_kwargs: dict[str, Any] = {}
        resolved_calibration = calibration_set_id or os.getenv("CLAIMSTAB_IQM_CALIBRATION_SET_ID")
        if resolved_calibration:
            backend_kwargs["calibration_set_id"] = resolved_calibration

        rows: list[dict[str, Any]] = []

        def _append_row(name: str | None, backend: Any, mode: str) -> None:
            backend_name_attr = getattr(backend, "name", None)
            backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
            rows.append(
                {
                    "name": str(backend_name_value or name or resolved_quantum_computer),
                    "mode": mode,
                    "num_qubits": int(getattr(backend, "num_qubits", 0) or 0),
                }
            )

        default_backend = provider.get_backend(**backend_kwargs)
        default_mode = "mock_hardware" if _is_mock_quantum_computer(resolved_quantum_computer) else "hardware"
        _append_row(None, default_backend, default_mode)

        if include_facades:
            for facade_name in _FACADE_BACKENDS:
                try:
                    facade_backend = provider.get_backend(facade_name, **backend_kwargs)
                except Exception:
                    continue
                _append_row(facade_name, facade_backend, "facade")

        return rows

    @staticmethod
    def _transpiled_stats(transpiled: QuantumCircuit) -> tuple[int, int]:
        two_qubit_count = 0
        swap_count = 0
        for item in transpiled.data:
            op = getattr(item, "operation", None)
            qubits = getattr(item, "qubits", None)
            if op is None or qubits is None:
                op = item[0]
                qubits = item[1]
            op_name = str(getattr(op, "name", ""))
            if len(qubits) == 2:
                two_qubit_count += 1
            if op_name == "swap":
                swap_count += 1
        return two_qubit_count, swap_count

    @staticmethod
    def _counts_from_job_result(job_result: Any) -> Counts:
        get_counts = getattr(job_result, "get_counts", None)
        if callable(get_counts):
            counts = get_counts()
            if isinstance(counts, list):
                if not counts:
                    raise ValueError("IQM job result returned an empty counts list.")
                counts = counts[0]
            return {str(k): int(v) for k, v in dict(counts).items()}
        raise ValueError("IQM job result does not expose get_counts().")

    def _transpile_cache_key(self, circuit: QuantumCircuit, cfg: Any) -> tuple[object, ...]:
        try:
            from qiskit import qasm2

            qasm = qasm2.dumps(circuit)
        except Exception:
            qasm = repr(circuit)
        backend_name_attr = getattr(self.backend, "name", None)
        backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
        return (
            qasm,
            str(backend_name_value or self.backend_name or self.quantum_computer),
            int(getattr(cfg, "optimization_level", 0)),
            getattr(cfg, "seed_transpiler", None),
            getattr(cfg, "layout_method", None),
        )

    def _transpile(self, circuit: QuantumCircuit, cfg: Any) -> QuantumCircuit:
        key = self._transpile_cache_key(circuit, cfg)
        cached = self._transpile_cache.get(key)
        if cached is not None:
            return cached
        transpiled = transpile(
            circuit,
            backend=self.backend,
            optimization_level=int(getattr(cfg, "optimization_level", 0)),
            seed_transpiler=getattr(cfg, "seed_transpiler", None),
            layout_method=getattr(cfg, "layout_method", None),
        )
        if self.cache_transpilation:
            self._transpile_cache[key] = transpiled
        return transpiled

    def run_counts(
        self,
        circuit: QuantumCircuit,
        cfg: Any,
        *,
        device_profile: DeviceProfile | None = None,
        device_backend=None,
        noise_model_mode: str = "none",
        device_snapshot_fingerprint: str | None = None,
        device_snapshot_summary: dict[str, object] | None = None,
    ) -> IQMRunResult:
        del device_profile, device_backend
        if noise_model_mode != "none":
            raise ValueError("IQM hardware runner does not support simulator noise-model injection.")

        wall_start = perf_counter()
        transpile_start = perf_counter()
        transpiled = self._transpile(circuit, cfg)
        transpile_ms = (perf_counter() - transpile_start) * 1000.0

        execute_start = perf_counter()
        job = self.backend.run(transpiled, shots=int(getattr(cfg, "shots", 1024)))
        counts = self._counts_from_job_result(job.result())
        execute_ms = (perf_counter() - execute_start) * 1000.0
        wall_ms = (perf_counter() - wall_start) * 1000.0

        two_qubit_count, swap_count = self._transpiled_stats(transpiled)
        backend_name_attr = getattr(self.backend, "name", None)
        backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
        return IQMRunResult(
            counts=counts,
            transpiled_depth=int(transpiled.depth()),
            transpiled_size=int(transpiled.size()),
            two_qubit_count=int(two_qubit_count),
            swap_count=int(swap_count),
            device_provider="iqm",
            device_name=str(backend_name_value or self.backend_name or self.quantum_computer),
            device_mode=self.device_mode,
            device_snapshot_fingerprint=device_snapshot_fingerprint or self.snapshot_fingerprint,
            device_snapshot_summary=device_snapshot_summary or self.snapshot,
            transpile_time_ms=transpile_ms,
            execute_time_ms=execute_ms,
            wall_time_ms=wall_ms,
        )

    def run_metric(
        self,
        circuit: QuantumCircuit,
        cfg: Any,
        metric_fn: MetricFn,
        *,
        return_details: bool = False,
        device_profile: DeviceProfile | None = None,
        device_backend=None,
        noise_model_mode: str = "none",
        device_snapshot_fingerprint: str | None = None,
        device_snapshot_summary: dict[str, object] | None = None,
    ):
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
