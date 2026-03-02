import unittest

from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace



def _small_space() -> PerturbationSpace:
    return PerturbationSpace(
        seeds_transpiler=[0, 1],
        opt_levels=[0],
        layout_methods=["trivial", "sabre"],
        shots_list=[64],
        seeds_simulator=[0],
    )


class TestSampling(unittest.TestCase):
    def test_full_factorial_sampling_returns_all(self) -> None:
        space = _small_space()
        sampled = sample_configs(space, SamplingPolicy(mode="full_factorial"))
        self.assertEqual(len(sampled), space.size())

    def test_random_k_sampling_respects_k(self) -> None:
        space = _small_space()
        sampled = sample_configs(space, SamplingPolicy(mode="random_k", sample_size=2, seed=0))
        self.assertEqual(len(sampled), 2)
        self.assertEqual(len(set(sampled)), 2)

    def test_ensure_config_included_adds_missing_baseline(self) -> None:
        baseline = PerturbationConfig(
            compilation=CompilationPerturbation(seed_transpiler=0, optimization_level=0, layout_method="trivial"),
            execution=ExecutionPerturbation(shots=64, seed_simulator=0),
        )
        other = PerturbationConfig(
            compilation=CompilationPerturbation(seed_transpiler=1, optimization_level=0, layout_method="sabre"),
            execution=ExecutionPerturbation(shots=64, seed_simulator=0),
        )

        out = ensure_config_included([other], baseline)
        self.assertEqual(out[0], baseline)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
