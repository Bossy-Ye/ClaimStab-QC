# Examples & Example Outputs

This page gives concrete run commands and representative output snippets.

## Example A — Core Stability Run

Command:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app \
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
    "reproduce_command": "PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app --suite core --sampling-mode random_k --sample-size 8 --sample-seed 1 --out-dir output/website_repro"
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
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.multidevice_app \
  --run all \
  --suite standard \
  --out-dir output/paper/multidevice
```

Output snippet (`output/paper/multidevice/transpile_only/transpile_only_summary.json`):
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

## Example D — External Task Plugin (module:Class)

Command:
```bash
python -m claimstab.cli run --spec examples/community/custom_task_demo/spec_toy.yml --out-dir output/examples/toy
```

Spec entrypoint:
```yaml
task:
  kind: external
  entrypoint: examples.community.custom_task_demo.toy_task:ToyTask
```

## Example E — Non-MaxCut BV -> ClaimAtlas (end-to-end)

Command:
```bash
PYTHONPATH=. ./.venv/bin/python examples/community/atlas_bv_workflow.py \
  --spec examples/community/specs/atlas_bv_demo.yml \
  --run-dir output/examples/atlas_bv_demo \
  --atlas-root atlas \
  --contributor your_name
```

What this does:
1. Runs BV decision-claim stability (`top_k=1`, `top_k=3`) using `examples/community/specs/atlas_bv_demo.yml`.
2. Publishes the run into `atlas/submissions/<submission_id>/`.
3. Validates `atlas/index.json` and artifact references.

Published artifacts:
- `atlas/submissions/<submission_id>/claim_stability.json`
- `atlas/submissions/<submission_id>/scores.csv`
- `atlas/submissions/<submission_id>/rq_summary.json`
- `atlas/submissions/<submission_id>/stability_report.html`
- `atlas/submissions/<submission_id>/metadata.json`

## Example F — Community-Contributed External Problem (Portfolio)

Command:
```bash
python -m claimstab.cli run --spec examples/community/community_contrib_demo/spec_portfolio.yml --out-dir output/examples/community_portfolio_demo --report
python -m claimstab.cli publish-result --run-dir output/examples/community_portfolio_demo --atlas-root atlas --contributor your_name
```

Notes:
- `UniformMix > Conservative` is typically stable in this demo.
- `RiskAware > UniformMix` is intentionally a harder claim and may be unstable/inconclusive under perturbations.

## Example G — Structural Compilation Benchmark (GHZ)

Command:
```bash
PYTHONPATH=. ./.venv/bin/python paper/experiments/scripts/exp_structural_compilation.py --out-dir output/paper/artifact/structural
```

What this evaluates:
1. `GHZ_Linear > GHZ_Star` on `circuit_depth` (`lower_is_better`).
2. `GHZ_Linear > GHZ_Star` on `two_qubit_count` (`lower_is_better`).

This provides a non-MaxCut, circuit-level benchmark class for compilation perturbation studies.
