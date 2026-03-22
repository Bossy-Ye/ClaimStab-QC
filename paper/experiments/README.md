# Paper Experiments

This directory is the paper-only experiment bundle used to reproduce evaluation artifacts.
It is intentionally separate from community onboarding examples.
The active paper rerun scaffold is split into:

- `specs/evaluation_v2/` -> core evaluation bundle in `output/paper/evaluation_v2/`
- `specs/evaluation_v3/` -> strengthening bundle in `output/paper/evaluation_v3/`

## Layout

- `specs/`: canonical paper specs.
- `scripts/`: canonical experiment batch scripts.
- core paper-facing generated outputs are stored under `output/paper/evaluation_v2/`.
- strengthening outputs are stored under `output/paper/evaluation_v3/`.
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
- E5: policy comparison on the expanded 495-configuration grid  
  Script: `scripts/exp_rq4_evaluation_v2.py`
- S1: backend-conditioned transpile-only structural portability  
  Spec: `specs/evaluation_v2/s1_multidevice_portability.yml`

Scope note:
- `S1` is intentionally narrower than a full noisy-device rerun and should be written as controlled structural portability.

## Active Evaluation v3

- W1-VQE: chemistry-flavored second-family pilot  
  Spec: `specs/evaluation_v3/w1_vqe_pilot.yml`
- W1-Max-2-SAT: counts-based second-family variational experiment  
  Spec: `specs/evaluation_v3/w1_max2sat_second_family.yml`
- W3: stronger metric-centric baselines  
  Script: `scripts/derive_rq1_metric_baselines_v3.py`
- W4: admissibility-study checklist and human-rating summary scaffold  
  Script: `scripts/summarize_admissibility_v3.py`
- W5: near-boundary policy comparison  
  Script: `scripts/exp_rq4_near_boundary_v3.py`

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
python paper/experiments/scripts/reproduce_evaluation_v3.py --layout-only
```

For individual runs, invoke the specs in both `paper/experiments/specs/evaluation_v2/` and `paper/experiments/specs/evaluation_v3/`.

W4 note:
- `paper/experiments/data/admissibility_v1/admissibility_items_v1.csv` includes admissible, non-admissible, and borderline items such as noise scaling and 10x shot budgets
- no rater CSVs are bundled as paper evidence; place real human labels under `paper/experiments/data/admissibility_v1/ratings/` before reporting kappa

Output conventions:
- core experiment outputs: `output/paper/evaluation_v2/runs/...`
- strengthening experiment outputs: `output/paper/evaluation_v3/runs/...`
- derived RQ tables/figures: `output/paper/evaluation_v2/{derived_paper_evaluation,pack}/...` and `output/paper/evaluation_v3/{derived_paper_evaluation,pack}/...`
