import unittest

from claimstab.claims.stability import estimate_binomial_rate
from claimstab.perturbations.sampling import (
    SamplingPolicy,
    adaptive_sample_configs,
    ensure_config_included,
    sample_configs,
)
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

    def test_adaptive_mode_uses_max_budget_for_initial_pool(self) -> None:
        space = _small_space()
        sampled = sample_configs(
            space,
            SamplingPolicy(mode="adaptive_ci", sample_size=3, seed=0),
        )
        self.assertEqual(len(sampled), 3)
        self.assertEqual(len(set(sampled)), 3)

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

    def test_adaptive_sample_configs_stops_on_target_width(self) -> None:
        space = _small_space()
        ordered = sample_configs(space, SamplingPolicy(mode="full_factorial"))

        def eval_prefix(prefix):
            n = len(prefix)
            # Becomes narrow only when enough prefixes are included.
            if n < 3:
                return estimate_binomial_rate(successes=1, total=2, confidence=0.95)
            return estimate_binomial_rate(successes=98, total=100, confidence=0.95)

        result = adaptive_sample_configs(
            ordered,
            evaluate_prefix=eval_prefix,
            target_ci_width=0.1,
            min_sample_size=1,
            step_size=1,
            max_sample_size=len(ordered),
        )
        self.assertEqual(result.stop_reason, "target_ci_width_reached")
        self.assertGreaterEqual(result.evaluated_configs, 3)


if __name__ == "__main__":
    unittest.main()
