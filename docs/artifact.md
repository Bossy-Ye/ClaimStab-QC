# Artifact Guide

## Environment
- Python `>=3.10`
- `qiskit`, `numpy`, `pandas`, `matplotlib`, `pyyaml`
- Optional:
  - `qiskit-aer` for Aer backend
  - `qiskit-ibm-runtime` for IBM fake device profiles

Install:
```bash
python -m pip install -e ".[aer,ibm,dev,docs]"
```

## Run Tests
```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
```

## Run Experiments
Main paper track (calibration):
```bash
PYTHONPATH=. ./.venv/bin/python examples/exp_comprehensive_calibration.py --out-dir output/presentation_large/calibration
```

Main paper track (large):
```bash
PYTHONPATH=. ./.venv/bin/python examples/exp_comprehensive_large.py --out-dir output/presentation_large/large
```

Legacy/core smoke:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app --suite core --out-dir output/core
```

Comprehensive:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --suite large \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode random_k \
  --sample-size 64 \
  --sample-seed 42 \
  --out-dir output/presentation_large/large/maxcut_ranking
```

Device-aware extension:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.multidevice_app --run all --suite standard --out-dir output/multidevice
```

## Validate Outputs
Check these fields in JSON:
- `meta.reproduce_command`
- `experiments[]`
- `overall.delta_sweep[]`
- `decision_counts`
- device metadata (for multi-device runs)

Lightweight structural invariant check:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.scripts.check_expected --out-dir output/expected_check --keep
```
