# claimstab/runners/matrix_runner.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping

from qiskit.transpiler import CouplingMap

from claimstab.cache.store import CacheStore
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

    @staticmethod
    def _circuit_digest(circuit: Any) -> str:
        try:
            from qiskit import qasm2  # type: ignore

            payload = qasm2.dumps(circuit)
        except Exception:
            payload = repr(circuit)
            # Default object repr embeds memory address, which is unstable across runs.
            if " object at 0x" in payload:
                payload = f"{type(circuit).__module__}.{type(circuit).__qualname__}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _config_dict(pc: PerturbationConfig) -> dict[str, Any]:
        return {
            "seed_transpiler": pc.compilation.seed_transpiler,
            "optimization_level": pc.compilation.optimization_level,
            "layout_method": pc.compilation.layout_method,
            "shots": pc.execution.shots,
            "seed_simulator": pc.execution.seed_simulator,
        }

    @staticmethod
    def _fingerprint(
        *,
        instance_id: str,
        method: MethodSpec,
        metric_name: str,
        circuit_digest: str,
        config: Mapping[str, Any],
        device_profile: DeviceProfile | None,
        noise_model_mode: str,
        runtime_context: Mapping[str, Any] | None,
    ) -> str:
        payload = {
            "instance_id": instance_id,
            "method": {
                "name": method.name,
                "kind": method.kind,
                "params": dict(method.params),
            },
            "metric_name": metric_name,
            "circuit_digest": circuit_digest,
            "config": dict(config),
            "device_profile": {
                "enabled": bool(getattr(device_profile, "enabled", False)),
                "provider": getattr(device_profile, "provider", None),
                "name": getattr(device_profile, "name", None),
                "mode": getattr(device_profile, "mode", None),
            },
            "noise_model_mode": noise_model_mode,
            "runtime_context": dict(runtime_context or {}),
        }
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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
        cache_store: CacheStore | None = None,
        runtime_context: Mapping[str, Any] | None = None,
        event_logger: Callable[[dict[str, Any]], None] | None = None,
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
            circuit_digest = self._circuit_digest(circuit)

            for pc in run_configs:
                comp = pc.compilation
                exe = pc.execution
                config_payload = self._config_dict(pc)
                fp = self._fingerprint(
                    instance_id=getattr(task, "instance_id", "unknown"),
                    method=method,
                    metric_name=metric_name,
                    circuit_digest=circuit_digest,
                    config=config_payload,
                    device_profile=device_profile,
                    noise_model_mode=noise_model_mode,
                    runtime_context=runtime_context,
                )
                if cache_store is not None:
                    cached = cache_store.get(fp)
                    if cached is not None:
                        if event_logger is not None:
                            event_logger(
                                {
                                    "event_type": "cache_hit",
                                    "instance_id": getattr(task, "instance_id", "unknown"),
                                    "method": method.name,
                                    "metric_name": metric_name,
                                    "config": config_payload,
                                    "fingerprint": fp,
                                }
                            )
                        rows.append(
                            ScoreRow(
                                instance_id=getattr(task, "instance_id", "unknown"),
                                seed_transpiler=comp.seed_transpiler,
                                optimization_level=comp.optimization_level,
                                transpiled_depth=int(cached["transpiled_depth"]),
                                transpiled_size=int(cached["transpiled_size"]),
                                method=method.name,
                                score=float(cached["score"]),
                                metric_name=metric_name,
                                layout_method=comp.layout_method,
                                seed_simulator=exe.seed_simulator,
                                shots=exe.shots,
                                device_provider=cached.get("device_provider"),
                                device_name=cached.get("device_name"),
                                device_mode=cached.get("device_mode"),
                                device_snapshot_fingerprint=cached.get("device_snapshot_fingerprint"),
                                circuit_depth=int(cached["transpiled_depth"]),
                                two_qubit_count=int(cached["two_qubit_count"]),
                                swap_count=int(cached["swap_count"]),
                                counts=(
                                    {str(k): int(v) for k, v in dict(cached.get("counts", {}) or {}).items()}
                                    if store_counts
                                    else None
                                ),
                            )
                        )
                        continue

                aer_cfg = AerRunConfig(
                    shots=exe.shots,
                    seed_simulator=exe.seed_simulator,
                    optimization_level=comp.optimization_level,
                    seed_transpiler=comp.seed_transpiler,
                    layout_method=comp.layout_method,
                    coupling_map=coupling_map,
                )
                if event_logger is not None:
                    event_logger(
                        {
                            "event_type": "run_start",
                            "instance_id": getattr(task, "instance_id", "unknown"),
                            "method": method.name,
                            "metric_name": metric_name,
                            "config": config_payload,
                            "fingerprint": fp,
                        }
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
                if cache_store is not None:
                    cache_store.put(
                        fp,
                        {
                            "score": float(effective_score),
                            "transpiled_depth": int(details.transpiled_depth),
                            "transpiled_size": int(details.transpiled_size),
                            "two_qubit_count": int(details.two_qubit_count),
                            "swap_count": int(details.swap_count),
                            "counts": (
                                {str(k): int(v) for k, v in dict(details.counts or {}).items()}
                                if details.counts is not None
                                else None
                            ),
                            "device_provider": details.device_provider,
                            "device_name": details.device_name,
                            "device_mode": details.device_mode,
                            "device_snapshot_fingerprint": details.device_snapshot_fingerprint,
                        },
                    )
                if event_logger is not None:
                    event_logger(
                        {
                            "event_type": "run_end",
                            "instance_id": getattr(task, "instance_id", "unknown"),
                            "method": method.name,
                            "metric_name": metric_name,
                            "config": config_payload,
                            "fingerprint": fp,
                            "score": float(effective_score),
                            "transpiled_depth": int(details.transpiled_depth),
                            "two_qubit_count": int(details.two_qubit_count),
                            "swap_count": int(details.swap_count),
                        }
                    )

        return rows
