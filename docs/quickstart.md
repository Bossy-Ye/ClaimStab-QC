# Quickstart

## Install

Core install:

```bash
python -m pip install -e .
```

With common extras:

```bash
python -m pip install -e ".[aer,ibm,docs,dev]"
```

CLI check:

```bash
python -m claimstab.cli --help
```

## Fastest Working Demo

Run the lightweight community demo:

```bash
python examples/community/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1
python -m claimstab.cli validate-evidence --json output/examples/claim_stability_demo/claim_stability.json
```

Expected outputs:

- `output/examples/claim_stability_demo/scores.csv`
- `output/examples/claim_stability_demo/claim_stability.json`
- `output/examples/claim_stability_demo/rq_summary.json`
- `output/examples/claim_stability_demo/robustness_map.json`
- `output/examples/claim_stability_demo/stability_report.html`

## Canonical Paper Run

Run the active E1 battleground:

```bash
python -m claimstab.cli validate-spec --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml \
  --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main \
  --report
python -m claimstab.cli validate-evidence \
  --json output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json
```

## Current Evaluation Tracks

Core paper-facing tracks:

- `paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml`
- `paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml`
- `paper/experiments/specs/evaluation_v2/e3_bv_decision.yml`
- `paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml`
- `paper/experiments/specs/evaluation_v2/s2_boundary.yml`
- `paper/experiments/specs/evaluation_v2/qec_portability.yml`

Practicality / supporting tracks:

- `paper/experiments/scripts/exp_rq4_evaluation_v2.py`
- `paper/experiments/specs/evaluation_v2/s1_multidevice_portability.yml`

## Generate Paper-facing Summaries and Figures

```bash
python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2
python paper/experiments/scripts/generate_eval_v2_focus_figures.py --root output/paper/evaluation_v2
```

Main figures will be staged under:

- `output/paper/evaluation_v2/pack/figures/main/`

## Community QEC Example

```bash
python -m claimstab.cli run \
  --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml \
  --out-dir output/examples/qec_pilot_demo \
  --report
```

## Useful CLI Options

- `--suite core|standard|large`
- `--sampling-mode full_factorial|random_k|adaptive_ci`
- `--sample-size N`
- `--out-dir output/<run_name>`

## Validation

```bash
./venv/bin/python -m pytest -q
./venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
./venv/bin/python -m mkdocs build --strict
```

## Notes

- Some older Atlas and external-task example scaffolds remain in the repository for reference, but they are not the canonical quickstart path.
- The active paper bundle is `output/paper/evaluation_v2/`, not the older `output/presentations/...` layout.
