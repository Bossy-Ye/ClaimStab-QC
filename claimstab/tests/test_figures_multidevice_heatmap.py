from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab.figures.plot_multidevice_heatmap import plot_multidevice_heatmaps


class TestMultideviceHeatmap(unittest.TestCase):
    def test_plot_multidevice_heatmaps(self) -> None:
        payload = {
            "device_summary": [
                {
                    "device_name": "FakeManilaV2",
                    "metric_name": "circuit_depth",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "delta": 0.0,
                    "stability_hat": 0.92,
                    "stability_ci_low": 0.88,
                    "decision": "inconclusive",
                },
                {
                    "device_name": "FakeKyoto",
                    "metric_name": "circuit_depth",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "delta": 0.0,
                    "stability_hat": 0.97,
                    "stability_ci_low": 0.94,
                    "decision": "stable",
                },
                {
                    "device_name": "FakeManilaV2",
                    "metric_name": "two_qubit_count",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "delta": 0.0,
                    "stability_hat": 0.90,
                    "stability_ci_low": 0.84,
                    "decision": "unstable",
                },
                {
                    "device_name": "FakeKyoto",
                    "metric_name": "two_qubit_count",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "delta": 0.0,
                    "stability_hat": 0.96,
                    "stability_ci_low": 0.93,
                    "decision": "stable",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            refs = plot_multidevice_heatmaps(payload, Path(td))
            st = refs.get("stability_hat_heatmap") or {}
            ci = refs.get("ci_low_heatmap") or {}
            self.assertTrue(Path(str(st.get("pdf"))).exists())
            self.assertTrue(Path(str(st.get("png"))).exists())
            self.assertTrue(Path(str(ci.get("pdf"))).exists())
            self.assertTrue(Path(str(ci.get("png"))).exists())


if __name__ == "__main__":
    unittest.main()
