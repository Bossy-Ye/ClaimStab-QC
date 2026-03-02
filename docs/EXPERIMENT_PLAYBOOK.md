# Experiment Playbook

This document provides recommended experiment profiles for paper-ready runs.

## 1) Fast Smoke Check
Use this before editing report scripts or claim logic.

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --out-dir output/smoke
```

## 2) Calibration Run (Deterministic)
Use `standard` suite and full-factorial to verify behavior and diagnostics.

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite standard \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode full_factorial \
  --deltas 0.0,0.01,0.05 \
  --out-dir output/exp_calibration
```

## 3) Large-Scale Run (Cost-Controlled)
Use `large` suite with random-k for broader evidence at practical cost.

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite large \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode random_k \
  --sample-size 64 \
  --sample-seed 42 \
  --deltas 0.0,0.01,0.05 \
  --out-dir output/exp_large
```

## 4) Multi-Device Run
Requires `qiskit-ibm-runtime` and `qiskit-aer`.

```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py \
  --run all \
  --suite standard \
  --out-dir output/multidevice
```

## 5) Report Generation
```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcache XDG_CACHE_HOME=/tmp/cache \
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/exp_large/claim_stability.json \
  --out output/exp_large/stability_report.html \
  --with-plots
```
