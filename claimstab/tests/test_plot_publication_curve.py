from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


class TestPublicationCurveScript(unittest.TestCase):
    def test_cli_writes_pdf_and_png(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_path = root / "curve.csv"
            out_base = root / "figure"
            df = pd.DataFrame(
                {
                    "x": [-3, -2, -1, 0, 1, 2, 3],
                    "y": [-0.04, -0.02, -0.01, 0.0, 0.015, 0.025, 0.03],
                    "ci_low": [-0.07, -0.05, -0.03, -0.01, 0.0, 0.01, 0.015],
                    "ci_high": [-0.01, 0.01, 0.01, 0.01, 0.03, 0.04, 0.045],
                }
            )
            df.to_csv(data_path, index=False)

            cmd = [
                sys.executable,
                "-m",
                "claimstab.scripts.plot_publication_curve",
                "--input",
                str(data_path),
                "--x-col",
                "x",
                "--y-col",
                "y",
                "--ci-low-col",
                "ci_low",
                "--ci-high-col",
                "ci_high",
                "--x-label",
                "event time",
                "--y-label",
                "effect",
                "--title",
                "Publication Test Figure",
                "--out",
                str(out_base),
            ]
            subprocess.run(cmd, check=True)

            self.assertTrue((root / "figure.pdf").exists())
            self.assertTrue((root / "figure.png").exists())


if __name__ == "__main__":
    unittest.main()
