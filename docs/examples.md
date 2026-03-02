# Examples & Example Outputs

This page gives concrete run commands and representative output snippets.

## Example A — Core Stability Run

Command:
```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1 \
  --out-dir output/website_repro
```

Output snippet (`output/website_repro/claim_stability.json`):
```json
{
  "meta": {
    "suite": "core",
    "reproduce_command": "PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py --suite core --sampling-mode random_k --sample-size 8 --sample-seed 1 --out-dir output/website_repro"
  },
  "overall": {
    "delta_sweep": [
      {
        "delta": 0.0,
        "stability_hat": 1.0,
        "stability_ci_low": 0.67559243511612,
        "stability_ci_high": 1.0,
        "decision": "inconclusive"
      }
    ]
  }
}
```

## Example B — Multi-device Transpile-only

Command:
```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py \
  --run all \
  --suite standard \
  --out-dir output/multidevice_full
```

Output snippet (`output/multidevice_full/transpile_only/transpile_only_summary.json`):
```json
{
  "batch": {
    "devices_requested": ["FakeManilaV2", "FakeBrisbane", "FakePrague", "FakeSherbrooke", "FakeKyoto", "FakeTorino"],
    "devices_completed": ["FakeBrisbane", "FakeKyoto", "FakePrague", "FakeSherbrooke", "FakeTorino"],
    "devices_skipped": [
      {
        "device_name": "FakeManilaV2",
        "reason": "No compatible instances for this device (device_qubits=5, suite=standard)."
      }
    ]
  }
}
```

Representative comparative row:
```json
{
  "batch_mode": "transpile_only",
  "device_name": "FakeBrisbane",
  "metric_name": "circuit_depth",
  "claim_pair": "QAOA_p1>QAOA_p2",
  "delta": 0.0,
  "stability_hat": 0.9898734177215189,
  "decision": "stable"
}
```

## Example C — Environment-dependent Noisy Sim Behavior

In this environment (Python 3.13), noisy simulation is skipped with explicit reason:
```json
{
  "batch_mode": "noisy_sim",
  "devices_skipped": [
    {
      "device_name": "FakeBrisbane",
      "reason": "noisy_sim skipped on Python 3.13 due known native qiskit-aer runtime instability in this environment."
    }
  ]
}
```

## Typical Artifacts
- `scores.csv`
- `claim_stability.json` or mode summary JSON
- `stability_report.html`
- `report_assets/*.png` (for plot-enabled reports)
