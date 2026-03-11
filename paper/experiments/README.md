# Paper Experiments

This directory is the paper-only experiment bundle used to reproduce evaluation artifacts.
It is intentionally separate from community onboarding examples.

## Layout

- `specs/`: canonical paper specs.
- `scripts/`: canonical experiment batch scripts.
- `summaries/`, `figures/`, `appendix/`: reserved staging locations for paper-facing assets.
- `_archive_legacy/`: archived legacy experiment artifacts/scripts.

## Canonical Experiments (Frozen)

- E1: MaxCut ranking prevalence/heterogeneity  
  Spec: `specs/paper_main.yml`
- E2: GHZ structural ranking control  
  Spec: `specs/paper_structural.yml`
- E3: BV decision control  
  Spec: `specs/paper_decision.yml`
- E4: Grover distribution stress  
  Spec: `specs/paper_distribution.yml`
- E5: Cost-confidence/adaptive comparison  
  Script: `scripts/exp_rq4_adaptive.py`

## Supporting Packs

- S1: Multidevice variability  
  Spec: `specs/paper_device.yml`
- S2: Boundary challenge  
  Spec/script: `specs/paper_boundary.yml`, `scripts/exp_boundary_challenge.py`
- S4: Synthetic truth calibration  
  Analysis command under `claimstab.analysis.synthetic_truth`

S3 methodset batch is optional and currently not part of core evidence.
In the frozen baseline evidence package, S3 is treated as non-evidence and can be left empty.

## Reproduction Entry

```bash
python -m claimstab.cli validate-spec --spec paper/experiments/specs/paper_main.yml
python -m claimstab.cli run --spec paper/experiments/specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report
```

For full matrix execution, use scripts in `paper/experiments/scripts/` or `make reproduce-paper`.

Output conventions:
- canonical experiment outputs: `output/presentation_large/...`
- paper packaging: `output/paper_pack/...`
