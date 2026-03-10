import unittest
from dataclasses import dataclass
import tempfile
from pathlib import Path

from claimstab.cache.store import CacheStore
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import PerturbationSpace
from claimstab.runners.matrix_runner import MatrixRunner


@dataclass(frozen=True)
class _Details:
    transpiled_depth: int
    transpiled_size: int
    two_qubit_count: int = 0
    swap_count: int = 0
    counts: dict[str, int] | None = None
    device_provider: str | None = None
    device_name: str | None = None
    device_mode: str | None = None
    device_snapshot_fingerprint: str | None = None
    transpile_time_ms: float | None = 1.0
    execute_time_ms: float | None = 2.0
    wall_time_ms: float | None = 3.0


class _Backend:
    def __init__(self) -> None:
        self.calls = 0

    def run_metric(self, circuit, cfg, metric_fn, *, return_details=False, **_kwargs):
        self.calls += 1
        details = _Details(transpiled_depth=7, transpiled_size=11)
        score = float(cfg.seed_transpiler)
        if return_details:
            return score, details
        return score


class _Task:
    instance_id = "dummy"

    def build(self, method):
        return object(), (lambda _counts: 0.0)


class TestMatrixRunner(unittest.TestCase):
    def test_runner_uses_provided_sampled_configs(self) -> None:
        space = PerturbationSpace(
            seeds_transpiler=[0, 1, 2],
            opt_levels=[0],
            layout_methods=["trivial"],
            shots_list=[64],
            seeds_simulator=[0],
        )
        sampled = list(space.iter_configs())[:1]

        runner = MatrixRunner(backend=_Backend())
        rows = runner.run(
            task=_Task(),
            methods=[
                MethodSpec(name="M1", kind="random"),
                MethodSpec(name="M2", kind="random"),
            ],
            space=space,
            configs=sampled,
            coupling_map=None,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({r.method for r in rows}, {"M1", "M2"})
        for row in rows:
            self.assertEqual(row.seed_transpiler, sampled[0].compilation.seed_transpiler)
            self.assertEqual(row.optimization_level, 0)

    def test_runner_supports_structural_metric_name(self) -> None:
        space = PerturbationSpace(
            seeds_transpiler=[0],
            opt_levels=[0],
            layout_methods=["trivial"],
            shots_list=[64],
            seeds_simulator=[0],
        )
        sampled = list(space.iter_configs())

        runner = MatrixRunner(backend=_Backend())
        rows = runner.run(
            task=_Task(),
            methods=[MethodSpec(name="M1", kind="random")],
            space=space,
            configs=sampled,
            coupling_map=None,
            metric_name="circuit_depth",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].score, 7.0)
        self.assertEqual(rows[0].transpile_time_ms, 1.0)
        self.assertEqual(rows[0].execute_time_ms, 2.0)
        self.assertEqual(rows[0].wall_time_ms, 3.0)

    def test_default_objective_path_is_device_neutral(self) -> None:
        space = PerturbationSpace(
            seeds_transpiler=[3],
            opt_levels=[0],
            layout_methods=["trivial"],
            shots_list=[64],
            seeds_simulator=[0],
        )
        sampled = list(space.iter_configs())

        runner = MatrixRunner(backend=_Backend())
        rows = runner.run(
            task=_Task(),
            methods=[MethodSpec(name="M1", kind="random")],
            space=space,
            configs=sampled,
            coupling_map=None,
            metric_name="objective",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].score, 3.0)
        self.assertIsNone(rows[0].device_provider)
        self.assertIsNone(rows[0].device_name)
        self.assertIsNone(rows[0].device_mode)

    def test_cache_hit_skips_backend_execution(self) -> None:
        space = PerturbationSpace(
            seeds_transpiler=[3],
            opt_levels=[0],
            layout_methods=["trivial"],
            shots_list=[64],
            seeds_simulator=[0],
        )
        sampled = list(space.iter_configs())
        backend = _Backend()
        runner = MatrixRunner(backend=backend)
        with tempfile.TemporaryDirectory() as td:
            cache = CacheStore(Path(td) / "cells.sqlite")
            events: list[dict[str, object]] = []
            try:
                rows1 = runner.run(
                    task=_Task(),
                    methods=[MethodSpec(name="M1", kind="random")],
                    space=space,
                    configs=sampled,
                    coupling_map=None,
                    metric_name="objective",
                    cache_store=cache,
                    runtime_context={"test": "yes"},
                    event_logger=events.append,
                )
                rows2 = runner.run(
                    task=_Task(),
                    methods=[MethodSpec(name="M1", kind="random")],
                    space=space,
                    configs=sampled,
                    coupling_map=None,
                    metric_name="objective",
                    cache_store=cache,
                    runtime_context={"test": "yes"},
                    event_logger=events.append,
                )
            finally:
                cache.close()
            self.assertEqual(backend.calls, 1)
            self.assertEqual(len(rows1), 1)
            self.assertEqual(len(rows2), 1)
            self.assertEqual(rows1[0].score, rows2[0].score)
            self.assertEqual(rows2[0].transpile_time_ms, 1.0)
            self.assertEqual(rows2[0].execute_time_ms, 2.0)
            self.assertEqual(rows2[0].wall_time_ms, 3.0)
            self.assertTrue(any(str(e.get("event_type")) == "cache_hit" for e in events))


if __name__ == "__main__":
    unittest.main()
