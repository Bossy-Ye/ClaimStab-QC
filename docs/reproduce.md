# Reproduce

This page lists the active commands for reproducing the current `evaluation_v2` bundle.

For the canonical command-to-directory mapping, see [Output Directory Map](output_map.md).
For the locked experiment set, see [Experiment Matrix](experiment_matrix.md).

## Canonical Output Roots

Preferred active roots:

- `output/paper/evaluation_v2/` for paper-facing experiments, derived tables, and figures
- `output/examples/` for lightweight community or onboarding runs
- `output/demos/` for local exploratory checks

Older roots such as `output/presentations/large/` and `output/paper/artifact/` are retained only in older commits and should not be used for new reproduction.

## 1) Create the `evaluation_v2` layout

```bash
python paper/experiments/scripts/reproduce_evaluation_v2.py --layout-only
```

This creates the expected directory scaffold and manifests under `output/paper/evaluation_v2/`.

## 2) Run the core paper experiments

### E1 — Main MaxCut battleground

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml \
  --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main \
  --report
python -m claimstab.cli validate-evidence \
  --json output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json
```

### E2 — GHZ structural calibration

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml \
  --out-dir output/paper/evaluation_v2/runs/E2_ghz_structural \
  --report
```

### E3 — BV decision calibration

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e3_bv_decision.yml \
  --out-dir output/paper/evaluation_v2/runs/E3_bv_decision \
  --report
```

### E4 — Grover distribution fragility case

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml \
  --out-dir output/paper/evaluation_v2/runs/E4_grover_distribution \
  --report
```

### S2 — Boundary stress

```bash
python paper/experiments/scripts/exp_boundary_challenge.py \
  --spec paper/experiments/specs/evaluation_v2/s2_boundary.yml \
  --out output/paper/evaluation_v2/runs/S2_boundary
```

### QEC — Supporting portability illustration

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/qec_portability.yml \
  --out-dir output/paper/evaluation_v2/runs/QEC_portability \
  --report
```

## 3) Run the practicality studies

### E5 — Policy comparison

```bash
python paper/experiments/scripts/exp_rq4_evaluation_v2.py \
  --out output/paper/evaluation_v2/runs/E5_policy_comparison
```

### S1 — Backend-conditioned structural portability

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/s1_multidevice_portability.yml \
  --out-dir output/paper/evaluation_v2/runs/S1_multidevice_portability
```

## 4) Derive paper-facing tables and summaries

```bash
python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2
```

This writes:

- `output/paper/evaluation_v2/derived_paper_evaluation/RQ1_necessity/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ2_semantics/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ3_diagnostics/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ4_practicality/`

## 5) Generate publication-facing figures

```bash
python paper/experiments/scripts/generate_eval_v2_focus_figures.py --root output/paper/evaluation_v2
python -m claimstab.figures.plot_rq4_adaptive \
  --input output/paper/evaluation_v2/runs/E5_policy_comparison/rq4_policy_summary.json \
  --out output/paper/evaluation_v2/runs/E5_policy_comparison/figures
```

Main figures are then staged under:

- `output/paper/evaluation_v2/pack/figures/main/`

## 6) Community-sized example

For a lightweight example outside the paper bundle:

```bash
python examples/community/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1
```

Default output:

- `output/examples/claim_stability_demo/`

## Validation and Docs

```bash
./venv/bin/python -m pytest -q
./venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
./venv/bin/python -m mkdocs build --strict
```

## Notes

- `S1` is currently a controlled transpile-only structural portability study rather than a full noisy-device rerun.
- Some older helper scripts in `examples/community/` remain in the repository for reference, but the commands on this page are the canonical active reproduction path.
