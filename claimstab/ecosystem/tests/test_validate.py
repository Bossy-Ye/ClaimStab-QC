from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from claimstab.ecosystem.validate import validate_ecosystem


class TestEcosystemValidate(unittest.TestCase):
    def test_repo_ecosystem_valid(self) -> None:
        result = validate_ecosystem("ecosystem")
        self.assertGreaterEqual(result.counts.get("tasks", 0), 1)
        self.assertGreaterEqual(result.counts.get("methods", 0), 1)
        self.assertGreaterEqual(result.counts.get("suites", 0), 1)

    def test_invalid_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "ecosystem"
            shutil.copytree(Path("ecosystem"), dst)
            target = dst / "methods" / "qaoa_p1" / "method.yaml"
            payload = yaml.safe_load(target.read_text(encoding="utf-8"))
            payload["task_ids"] = ["does_not_exist"]
            target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_ecosystem(dst)


if __name__ == "__main__":
    unittest.main()
