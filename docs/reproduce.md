# Reproduce

This page lists exact commands captured in result JSON metadata (`meta.reproduce_command`).

## Command 1 — Core Claim Stability Run
From `output/website_repro/claim_stability.json`:

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py --suite core --sampling-mode random_k --sample-size 8 --sample-seed 1 --out-dir output/website_repro
```

## Command 2 — Multi-device Run
From `output/multidevice_full/transpile_only/transpile_only_summary.json`:

```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py --run all --suite standard --out-dir output/multidevice_full
```

## Expected Artifacts
- `scores.csv`
- `claim_stability.json` (or mode-specific summary JSON)
- `stability_report.html`

## Runtime Expectations
- `core` smoke runs: short.
- `standard`/`large` comprehensive runs: moderate to long.
- multi-device transpile-only: moderate (depends on number of devices and sampled configs).
- noisy simulation: longer and environment dependent.
