from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qiskit import qasm2

from claimstab import cli
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import (
    CompilationPerturbation,
    ExecutionPerturbation,
    HybridOptimizationPerturbation,
    PerturbationConfig,
)
from claimstab.tasks.instances import ProblemInstance
from examples.community.max2sat_pilot_demo.max2sat_task import Max2SATPayload, Max2SATQAOAPilotTask, _core_instances


class TestMax2SATPilotDemo(unittest.TestCase):
    def test_max2sat_pilot_spec_runs_end_to_end(self) -> None:
        spec_path = Path("examples/community/max2sat_pilot_demo/spec_max2sat.yml")
        self.assertTrue(spec_path.exists())

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "max2sat_pilot"
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(out_dir),
                    "--validate",
                ]
            )
            self.assertEqual(rc, 0)

            payload = json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("meta", {}).get("task"), "max2sat_qaoa_pilot")
            experiments = payload.get("experiments", [])
            self.assertEqual(len(experiments), 6)
            for experiment in experiments:
                claim = experiment.get("claim", {})
                self.assertEqual(claim.get("metric_name"), "objective")
                self.assertTrue(bool(claim.get("higher_is_better", True)))
                delta_sweep = experiment.get("overall", {}).get("delta_sweep", [])
                self.assertEqual(len(delta_sweep), 3)


class TestMax2SATHybridInitialization(unittest.TestCase):
    def setUp(self) -> None:
        payload = _core_instances()[0]
        self.instance = ProblemInstance(instance_id="max2sat_hybrid_test", payload=payload)
        self.method = MethodSpec(name="QAOA_p2", kind="qaoa", params={"p": 2})

    @staticmethod
    def _cfg(seed: int) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=CompilationPerturbation(seed_transpiler=0, optimization_level=1, layout_method="sabre"),
            execution=ExecutionPerturbation(shots=256, seed_simulator=0),
            hybrid_opt=HybridOptimizationPerturbation(init_strategy="random", init_seed=seed),
        )

    def test_random_init_is_seed_deterministic(self) -> None:
        task = Max2SATQAOAPilotTask(
            num_instances=6,
            hybrid_optimization={
                "enabled": True,
                "init_strategies": ["random"],
                "init_seeds": [0, 1, 2],
            },
        )
        c1 = task.build_with_config(self.instance, self.method, self._cfg(3)).circuit
        c2 = task.build_with_config(self.instance, self.method, self._cfg(3)).circuit
        c3 = task.build_with_config(self.instance, self.method, self._cfg(4)).circuit

        self.assertEqual(c1.count_ops(), c2.count_ops())
        self.assertEqual(qasm2.dumps(c1), qasm2.dumps(c2))
        self.assertNotEqual(qasm2.dumps(c1), qasm2.dumps(c3))

    def test_hybrid_axes_exposed_only_when_enabled(self) -> None:
        disabled = Max2SATQAOAPilotTask()
        self.assertEqual(disabled.hybrid_space_axes(), (None, None))

        enabled = Max2SATQAOAPilotTask(
            hybrid_optimization={
                "enabled": True,
                "init_strategies": ["fixed", "random"],
                "init_seeds": [0, 1],
            }
        )
        strategies, seeds = enabled.hybrid_space_axes()
        self.assertEqual(strategies, ["fixed", "random"])
        self.assertEqual(seeds, [0, 1])


if __name__ == "__main__":
    unittest.main()
