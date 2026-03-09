from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestExpRQ4AdaptiveScript(unittest.TestCase):
    def _write_claim_json(
        self,
        path: Path,
        *,
        sampling_mode: str,
        k_used: int,
        decisions: tuple[str, str],
        adaptive_enabled: bool = False,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        sampling_payload: dict[str, object] = {
            "mode": sampling_mode,
            "sampled_configurations_with_baseline": k_used,
            "sample_size": k_used if sampling_mode == "random_k" else None,
            "perturbation_space_size": 128,
        }
        if adaptive_enabled:
            sampling_payload["adaptive_stopping"] = {
                "enabled": True,
                "target_ci_width": 0.05,
                "achieved_ci_width": 0.043,
                "selected_configurations_with_baseline": k_used,
                "stop_reason": "target_ci_width_reached",
            }

        payload = {
            "experiments": [{"sampling": sampling_payload}],
            "comparative": {
                "space_claim_delta": [
                    {
                        "delta": 0.0,
                        "decision": decisions[0],
                        "stability_hat": 0.90,
                        "stability_ci_low": 0.80,
                        "stability_ci_high": 0.96,
                        "n_claim_evals": 800,
                    },
                    {
                        "delta": 0.01,
                        "decision": decisions[1],
                        "stability_hat": 0.86,
                        "stability_ci_low": 0.74,
                        "stability_ci_high": 0.93,
                        "n_claim_evals": 800,
                    },
                ]
            },
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def test_skip_run_builds_summary_and_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "rq4_adaptive"
            runs_dir = out_dir / "runs"

            self._write_claim_json(
                runs_dir / "full_factorial" / "claim_stability.json",
                sampling_mode="full_factorial",
                k_used=128,
                decisions=("stable", "stable"),
            )
            self._write_claim_json(
                runs_dir / "random_k_32" / "claim_stability.json",
                sampling_mode="random_k",
                k_used=32,
                decisions=("stable", "unstable"),
            )
            self._write_claim_json(
                runs_dir / "random_k_64" / "claim_stability.json",
                sampling_mode="random_k",
                k_used=64,
                decisions=("stable", "stable"),
            )
            self._write_claim_json(
                runs_dir / "adaptive_ci" / "claim_stability.json",
                sampling_mode="adaptive_ci",
                k_used=56,
                decisions=("stable", "stable"),
                adaptive_enabled=True,
            )

            cmd = [
                sys.executable,
                "examples/exp_rq4_adaptive.py",
                "--out",
                str(out_dir),
                "--skip-run",
            ]
            subprocess.run(cmd, check=True)

            summary_path = out_dir / "rq4_adaptive_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            strategies = summary.get("strategies", [])
            self.assertEqual(len(strategies), 4)

            by_name = {str(row.get("strategy")): row for row in strategies if isinstance(row, dict)}
            self.assertEqual(by_name["full_factorial"].get("agreement_with_factorial", {}).get("rate"), 1.0)
            self.assertEqual(by_name["random_k_32"].get("agreement_with_factorial", {}).get("rate"), 0.5)
            self.assertEqual(by_name["random_k_64"].get("agreement_with_factorial", {}).get("rate"), 1.0)
            self.assertEqual(by_name["adaptive_ci"].get("agreement_with_factorial", {}).get("rate"), 1.0)

            figures = summary.get("figures", {})
            ci_ref = figures.get("ci_width_vs_cost", {}) if isinstance(figures, dict) else {}
            ag_ref = figures.get("agreement_vs_cost", {}) if isinstance(figures, dict) else {}
            self.assertTrue(Path(str(ci_ref.get("pdf"))).exists())
            self.assertTrue(Path(str(ci_ref.get("png"))).exists())
            self.assertTrue(Path(str(ag_ref.get("pdf"))).exists())
            self.assertTrue(Path(str(ag_ref.get("png"))).exists())


if __name__ == "__main__":
    unittest.main()
