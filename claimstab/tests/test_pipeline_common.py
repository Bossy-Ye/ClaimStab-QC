from __future__ import annotations

import unittest

from claimstab.pipelines.common import (
    baseline_from_keys,
    build_baseline_config,
    canonical_space_name,
    canonical_suite_name,
    make_space,
    parse_claim_pairs,
    parse_deltas,
)
from claimstab.perturbations.space import PerturbationSpace


class TestPipelineCommon(unittest.TestCase):
    def test_parse_deltas_requires_non_empty(self) -> None:
        with self.assertRaises(ValueError):
            parse_deltas("")
        self.assertEqual(parse_deltas("0.0,0.05"), [0.0, 0.05])

    def test_parse_claim_pairs_supports_fallback(self) -> None:
        self.assertEqual(
            parse_claim_pairs("", fallback_pair=("A", "B")),
            [("A", "B")],
        )
        self.assertEqual(
            parse_claim_pairs("A>B,C:D", require_distinct=True),
            [("A", "B"), ("C", "D")],
        )
        with self.assertRaises(ValueError):
            parse_claim_pairs("A>A", require_distinct=True)

    def test_canonical_aliases(self) -> None:
        self.assertEqual(canonical_suite_name("day1"), "core")
        self.assertEqual(canonical_space_name("day1_default", space_label="space"), "baseline")

    def test_make_space_combined_light_override(self) -> None:
        space = make_space("combined_light", combined_light_shots=[64, 256, 1024])
        self.assertIsInstance(space, PerturbationSpace)
        self.assertEqual(space.shots_list, [64, 256, 1024])

    def test_baseline_helpers(self) -> None:
        space = make_space("baseline")
        baseline_cfg, baseline_pc, baseline_key = build_baseline_config(space)
        self.assertEqual(baseline_key[0], baseline_pc.compilation.seed_transpiler)
        recovered_cfg, recovered_key = baseline_from_keys({baseline_key})
        self.assertEqual(recovered_key, baseline_key)
        self.assertEqual(recovered_cfg["shots"], baseline_cfg["shots"])


if __name__ == "__main__":
    unittest.main()
