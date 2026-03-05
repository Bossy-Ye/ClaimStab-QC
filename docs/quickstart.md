# Quickstart

## Install
Core install:

```bash
python -m pip install -e .
```

CLI check:
```bash
claimstab --help
```

With optional extras:

```bash
python -m pip install -e ".[aer,ibm,docs,dev]"
```

## Minimal Run
Run a small claim-stability demo:

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1 \
  --out-dir output/quickstart
```

Expected outputs:
- `output/quickstart/scores.csv`
- `output/quickstart/claim_stability.json`

Equivalent CLI run from spec:
```bash
claimstab validate-spec --spec specs/paper_main.yml
claimstab run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report
```

## Evaluation Tracks
Main paper tracks:
```bash
PYTHONPATH=. ./venv/bin/python examples/exp_comprehensive_calibration.py
PYTHONPATH=. ./venv/bin/python examples/exp_comprehensive_large.py
PYTHONPATH=. ./venv/bin/python examples/exp_structural_compilation.py
```

Device-targeted extension:
```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py --run all --suite standard --out-dir output/multidevice_full
```

External task plugin demo:
```bash
claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy
```

Generate your own external-task starter:
```bash
claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo
```

Then run it:
```bash
claimstab run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
```

One-command artifact build (experiments + reports + figures):
```bash
make reproduce-paper
```

## Generate HTML Report
```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/quickstart/claim_stability.json \
  --out output/quickstart/stability_report.html
```

## Useful CLI Options
- `--suite core|standard|large`
- `--space-preset baseline|compilation_only|sampling_only|combined_light`
- `--space-presets ...` for comparative multi-space runs
- `--claim-pairs "A>B,C>D"` for batch claim evaluation
- `--sampling-mode full_factorial|random_k`
- `--sample-size N` (with `random_k`)
- `--out-dir output/<run_name>`

## Spec Format
Template specs are available in:
- `examples/specs/claim_spec.yaml`
- `examples/specs/perturbation_spec.yaml`

Example run with a spec file:

```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite core \
  --spec examples/specs/claim_spec.yaml \
  --out-dir output/spec_run
```

Plot-enabled report:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcache XDG_CACHE_HOME=/tmp/cache \
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/quickstart/claim_stability.json \
  --out output/quickstart/stability_report_plots.html \
  --with-plots
```
