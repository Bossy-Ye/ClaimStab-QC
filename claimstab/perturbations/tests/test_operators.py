import unittest

from claimstab.perturbations.operators import (
    LayoutMethodOperator,
    OptimizationLevelOperator,
    SeedSimulatorOperator,
    SeedTranspilerOperator,
    ShotsOperator,
    iter_space_configs_via_operators,
)
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace


class TestPerturbationOperators(unittest.TestCase):
    def test_single_operator_apply(self) -> None:
        base = PerturbationConfig(
            compilation=CompilationPerturbation(seed_transpiler=0, optimization_level=1, layout_method="sabre"),
            execution=ExecutionPerturbation(shots=256, seed_simulator=3),
        )
        cfg = SeedTranspilerOperator(9).apply(base)
        cfg = OptimizationLevelOperator(3).apply(cfg)
        cfg = LayoutMethodOperator("trivial").apply(cfg)
        cfg = ShotsOperator(1024).apply(cfg)
        cfg = SeedSimulatorOperator(7).apply(cfg)

        self.assertEqual(cfg.compilation.seed_transpiler, 9)
        self.assertEqual(cfg.compilation.optimization_level, 3)
        self.assertEqual(cfg.compilation.layout_method, "trivial")
        self.assertEqual(cfg.execution.shots, 1024)
        self.assertEqual(cfg.execution.seed_simulator, 7)

    def test_operator_shim_matches_sampling_only_space(self) -> None:
        space = PerturbationSpace.sampling_only()
        classic = list(space.iter_configs())
        shim = list(space.iter_configs_with_operators())
        self.assertEqual(len(shim), len(classic))
        self.assertEqual(shim, classic)

    def test_standalone_iter_space_configs_via_operators(self) -> None:
        space = PerturbationSpace(
            seeds_transpiler=[0, 1],
            opt_levels=[1],
            layout_methods=["sabre"],
            shots_list=[64, 256],
            seeds_simulator=[0, 1],
        )
        configs = list(iter_space_configs_via_operators(space))
        self.assertEqual(len(configs), space.size())


if __name__ == "__main__":
    unittest.main()
