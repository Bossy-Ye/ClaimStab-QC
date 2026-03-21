# Paper Experiments

This directory is the paper-only experiment bundle used to reproduce evaluation artifacts.
It is intentionally separate from community onboarding examples.
The active rerun scaffold now lives under `specs/evaluation_v2/` and writes into `output/paper/evaluation_v2/`.

## Layout

- `specs/`: canonical paper specs.
- `scripts/`: canonical experiment batch scripts.
- active paper-facing generated outputs are stored under `output/paper/evaluation_v2/`.
- `_archive_legacy/`: archived legacy experiment artifacts/scripts.

## Active Evaluation v2

- E1: MaxCut main battleground  
  Spec: `specs/evaluation_v2/e1_maxcut_main.yml`
- E2: GHZ structural calibration  
  Spec: `specs/evaluation_v2/e2_ghz_structural.yml`
- E3: BV decision calibration  
  Spec: `specs/evaluation_v2/e3_bv_decision.yml`
- E4: Grover distribution fragility case  
  Spec: `specs/evaluation_v2/e4_grover_distribution.yml`
- S2: Boundary challenge  
  Spec: `specs/evaluation_v2/s2_boundary.yml`
- QEC: supporting portability illustration  
  Spec: `specs/evaluation_v2/qec_portability.yml`

Staged but not yet finalized:
- E5: multi-claim policy comparison
- S1: multidevice portability

## Supporting / Legacy Scripts

- E5 legacy adaptive study: `scripts/exp_rq4_adaptive.py`
- S4 synthetic calibration: `claimstab.analysis.synthetic_truth`
- S5 mutation sanity check: `scripts/exp_mutation_sanity.py`

S3 methodset batch is optional and currently not part of core evidence.
It is treated as non-evidence and can be left empty.

## Reproduction Entry

```bash
python paper/experiments/scripts/reproduce_evaluation_v2.py --layout-only
python paper/experiments/scripts/reproduce_evaluation_v2.py
```

For individual runs, invoke the specs in `paper/experiments/specs/evaluation_v2/`.

Output conventions:
- canonical experiment outputs: `output/paper/evaluation_v2/runs/...`
- derived RQ tables/figures: `output/paper/evaluation_v2/{derived,pack}/...`
