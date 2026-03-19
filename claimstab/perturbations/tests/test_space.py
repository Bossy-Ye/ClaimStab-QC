import unittest

from claimstab.perturbations.space import PerturbationSpace


class TestSpace(unittest.TestCase):
    def test_baseline_space_constructs_and_has_expected_size(self) -> None:
        space = PerturbationSpace.conf_level_default()

        self.assertEqual(space.size(), 10 * 4 * 2 * 1 * 1)

        first = next(space.iter_configs())
        self.assertEqual(first.execution.shots, 1024)
        self.assertEqual(first.execution.seed_simulator, 0)

    def test_exact_eval_spaces_have_expected_sizes(self) -> None:
        self.assertEqual(PerturbationSpace.compilation_only_exact().size(), 27)
        self.assertEqual(PerturbationSpace.sampling_only_exact().size(), 20)
        self.assertEqual(PerturbationSpace.combined_light_exact().size(), 30)
        self.assertEqual(PerturbationSpace.sampling_policy_eval().size(), 495)

    def test_exact_compilation_space_uses_three_layout_methods(self) -> None:
        first_space = PerturbationSpace.compilation_only_exact()
        self.assertEqual(first_space.layout_methods, ["trivial", "dense", "sabre"])


if __name__ == "__main__":
    unittest.main()
