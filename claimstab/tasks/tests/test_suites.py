from __future__ import annotations

import unittest

from claimstab.tasks.suites import load_suite


class TestSuites(unittest.TestCase):
    def test_load_standard_suite(self) -> None:
        suite = load_suite("standard")
        self.assertEqual(len(suite), 5)
        self.assertEqual(suite[0].instance_id, "ring6")

    def test_alias_day2_maps_to_standard(self) -> None:
        suite = load_suite("day2")
        self.assertEqual(len(suite), 5)


if __name__ == "__main__":
    unittest.main()
