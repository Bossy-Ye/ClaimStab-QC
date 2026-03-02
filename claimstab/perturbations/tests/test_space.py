import unittest

from claimstab.perturbations.space import PerturbationSpace


class TestSpace(unittest.TestCase):
    def test_baseline_space_constructs_and_has_expected_size(self) -> None:
        space = PerturbationSpace.conf_level_default()

        self.assertEqual(space.size(), 10 * 4 * 2 * 1 * 1)

        first = next(space.iter_configs())
        self.assertEqual(first.execution.shots, 1024)
        self.assertEqual(first.execution.seed_simulator, 0)


if __name__ == "__main__":
    unittest.main()
