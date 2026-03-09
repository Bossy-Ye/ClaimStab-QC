# Experiment Playbook

This document provides recommended experiment profiles for paper-ready runs.
For the canonical command-to-directory mapping, see [Output Directory Map](output_map.md).

## 1) Fast Smoke Check
Use this before editing report scripts or claim logic.

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --out-dir output/presentation/main/maxcut_core_smoke
```

## 2) Calibration Run (Deterministic)
Use `standard` suite and full-factorial to verify behavior and diagnostics.

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --suite standard \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode full_factorial \
  --deltas 0.0,0.01,0.05 \
  --out-dir output/presentation_large/calibration/maxcut_ranking
```

## 3) Large-Scale Run (Cost-Controlled)
Use `large` suite with random-k for broader evidence at practical cost.

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --suite large \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode random_k \
  --sample-size 64 \
  --sample-seed 42 \
  --deltas 0.0,0.01,0.05 \
  --out-dir output/presentation_large/large/maxcut_ranking
```

## 4) Multi-Device Run
Requires `qiskit-ibm-runtime` and `qiskit-aer`.

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.pipelines.multidevice_app \
  --run all \
  --suite standard \
  --out-dir output/multidevice
```

## 5) Report Generation
```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcache XDG_CACHE_HOME=/tmp/cache \
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/presentation_large/large/maxcut_ranking/claim_stability.json \
  --out output/presentation_large/large/maxcut_ranking/stability_report.html \
  --with-plots

python -m claimstab.cli validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json
```

## Output Path Convention

Preferred (paper/submission):
- `output/paper_artifact/` (from `make reproduce-paper`)
- `output/presentation/` (core curated package)
- `output/presentation_large/` (extended curated package)

Optional legacy ad-hoc paths:
- `output/exp_*`
