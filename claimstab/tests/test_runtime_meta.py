from __future__ import annotations

import unittest

from claimstab.io.runtime_meta import collect_runtime_metadata


class TestRuntimeMetadata(unittest.TestCase):
    def test_collect_runtime_metadata_default_shape(self) -> None:
        meta = collect_runtime_metadata()
        self.assertIn("python_version", meta)
        self.assertIn("platform", meta)
        self.assertIn("dependencies", meta)
        self.assertIn("environment_flags", meta)
        self.assertIn("git_commit", meta)
        self.assertIn("git_dirty", meta)
        self.assertIsInstance(meta["dependencies"], dict)
        self.assertIsInstance(meta["environment_flags"], dict)

    def test_collect_runtime_metadata_lightweight_mode(self) -> None:
        meta = collect_runtime_metadata(
            include_dependencies=False,
            include_environment_flags=False,
            include_git=False,
        )
        self.assertEqual(meta["dependencies"], {})
        self.assertEqual(
            meta["environment_flags"],
            {"aer_available": None, "ibm_runtime_available": None},
        )
        self.assertIsNone(meta["git_commit"])
        self.assertIsNone(meta["git_dirty"])


if __name__ == "__main__":
    unittest.main()
