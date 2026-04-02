from __future__ import annotations

from dataclasses import dataclass
import os
from time import perf_counter
from typing import Any, Callable

from qiskit import QuantumCircuit, transpile

from claimstab.devices.ibm_fake import fingerprint, snapshot_from_backend
from claimstab.devices.spec import DeviceProfile


type Counts = dict[str, int]
type MetricFn = Callable[[Counts], float]


@dataclass(frozen=True, slots=True)
class IBMRuntimeRunResult:
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


def _load_runtime_types():
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except Exception as exc:  # pragma: no cover - import path depends on optional dep
        raise ImportError(
            "IBM runtime support requires qiskit-ibm-runtime. Install with:\n"
            "  pip install 'claimstab-qc[ibm]'"
        ) from exc
    return QiskitRuntimeService, SamplerV2


class QiskitIBMRuntimeRunner:
    """Minimal real-hardware runner for small ClaimStab slices.

    This runner intentionally targets small, explicit hardware slices rather than
    the full paper matrix. It uses IBM Runtime SamplerV2 and converts measured
    bit arrays back into counts so the existing claim-centric pipeline can be
    reused without changing claim semantics.
    """

    def __init__(
        self,
        engine: str | None = None,
        *,
        backend_name: str | None = None,
        channel: str | None = None,
        instance: str | None = None,
        token: str | None = None,
        token_env: str = "IBM_QUANTUM_TOKEN",
        account_name: str | None = None,
        cache_transpilation: bool = True,
        **_: Any,
    ) -> None:
        del engine  # kept for drop-in compatibility with the Aer runner constructor
        self.backend_name = backend_name or os.getenv("CLAIMSTAB_IBM_BACKEND")
        if not self.backend_name:
            raise ValueError(
                "IBM hardware execution requires a backend name. "
                "Set CLAIMSTAB_IBM_BACKEND or pass backend_name explicitly."
            )

        self.channel = channel or os.getenv("CLAIMSTAB_IBM_CHANNEL", "ibm_quantum_platform")
        self.instance = instance or os.getenv("CLAIMSTAB_IBM_INSTANCE")
        self.token = token if token is not None else os.getenv(token_env)
        self.account_name = account_name or os.getenv("CLAIMSTAB_IBM_ACCOUNT_NAME")
        self.cache_transpilation = bool(cache_transpilation)
        self._transpile_cache: dict[tuple[object, ...], QuantumCircuit] = {}

        service_cls, sampler_cls = _load_runtime_types()
        service_kwargs: dict[str, Any] = {"channel": self.channel}
        if self.token:
            service_kwargs["token"] = self.token
        if self.instance:
            service_kwargs["instance"] = self.instance
        if self.account_name:
            service_kwargs["name"] = self.account_name

        self.service = service_cls(**service_kwargs)
        self.backend = self.service.backend(self.backend_name, instance=self.instance)
        self.sampler = sampler_cls(mode=self.backend)

        try:
            snap = snapshot_from_backend(self.backend)
        except Exception:
            backend_name_attr = getattr(self.backend, "name", None)
            backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
            snap = {
                "backend_name": str(backend_name_value or self.backend_name),
                "backend_class": type(self.backend).__name__,
                "num_qubits": int(getattr(self.backend, "num_qubits", 0) or 0),
            }
        self.snapshot = snap
        self.snapshot_fingerprint = fingerprint(snap)

    @staticmethod
    def available_backends(
        *,
        channel: str | None = None,
        instance: str | None = None,
        token: str | None = None,
        token_env: str = "IBM_QUANTUM_TOKEN",
        account_name: str | None = None,
        min_num_qubits: int | None = None,
    ) -> list[dict[str, Any]]:
        service_cls, _ = _load_runtime_types()
        service_kwargs: dict[str, Any] = {
            "channel": channel or os.getenv("CLAIMSTAB_IBM_CHANNEL", "ibm_quantum_platform")
        }
        resolved_token = token if token is not None else os.getenv(token_env)
        resolved_instance = instance or os.getenv("CLAIMSTAB_IBM_INSTANCE")
        resolved_name = account_name or os.getenv("CLAIMSTAB_IBM_ACCOUNT_NAME")
        if resolved_token:
            service_kwargs["token"] = resolved_token
        if resolved_instance:
            service_kwargs["instance"] = resolved_instance
        if resolved_name:
            service_kwargs["name"] = resolved_name
        service = service_cls(**service_kwargs)
        backends = service.backends(instance=resolved_instance, min_num_qubits=min_num_qubits)
        rows: list[dict[str, Any]] = []
        for backend in backends:
            name_attr = getattr(backend, "name", None)
            name_value = name_attr() if callable(name_attr) else name_attr
            rows.append(
                {
                    "name": str(name_value),
                    "num_qubits": int(getattr(backend, "num_qubits", 0) or 0),
                    "status": str(getattr(backend, "status", lambda: "unknown")()),
                }
            )
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
    def _counts_from_pub_result(pub_result: Any) -> Counts:
        join_data = getattr(pub_result, "join_data", None)
        if callable(join_data):
            joined = join_data()
            get_counts = getattr(joined, "get_counts", None)
            if callable(get_counts):
                return {str(k): int(v) for k, v in dict(get_counts()).items()}

        data = getattr(pub_result, "data", None)
        if data is not None:
            for name in dir(data):
                if name.startswith("_"):
                    continue
                try:
                    slot = getattr(data, name)
                except Exception:
                    continue
                get_counts = getattr(slot, "get_counts", None)
                if callable(get_counts):
                    return {str(k): int(v) for k, v in dict(get_counts()).items()}

        raise ValueError("Sampler result does not expose measurable counts.")

    def _transpile_cache_key(self, circuit: QuantumCircuit, cfg: Any) -> tuple[object, ...]:
        qasm = None
        try:
            from qiskit import qasm2

            qasm = qasm2.dumps(circuit)
        except Exception:
            qasm = repr(circuit)
        return (
            qasm,
            str(self.backend_name),
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
    ) -> IBMRuntimeRunResult:
        del device_profile, device_backend
        if noise_model_mode != "none":
            raise ValueError("IBM hardware runner does not support simulator noise-model injection.")

        wall_start = perf_counter()
        transpile_start = perf_counter()
        transpiled = self._transpile(circuit, cfg)
        transpile_ms = (perf_counter() - transpile_start) * 1000.0

        execute_start = perf_counter()
        job = self.sampler.run([transpiled], shots=int(getattr(cfg, "shots", 1024)))
        pub_result = job.result()[0]
        counts = self._counts_from_pub_result(pub_result)
        execute_ms = (perf_counter() - execute_start) * 1000.0
        wall_ms = (perf_counter() - wall_start) * 1000.0

        two_qubit_count, swap_count = self._transpiled_stats(transpiled)
        backend_name_attr = getattr(self.backend, "name", None)
        backend_name_value = backend_name_attr() if callable(backend_name_attr) else backend_name_attr
        return IBMRuntimeRunResult(
            counts=counts,
            transpiled_depth=int(transpiled.depth()),
            transpiled_size=int(transpiled.size()),
            two_qubit_count=int(two_qubit_count),
            swap_count=int(swap_count),
            device_provider="ibm_runtime",
            device_name=str(backend_name_value or self.backend_name),
            device_mode="hardware",
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

