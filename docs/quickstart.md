# Quickstart

## Install
Core install:

```bash
python -m pip install -e .
```

CLI check:
```bash
python -m claimstab.cli --help
```

With optional extras:

```bash
python -m pip install -e ".[aer,ibm,docs,dev]"
```

## Minimal Run
Run a small claim-stability demo:

```bash
python -m claimstab.cli validate-spec --spec specs/atlas_bv_demo.yml
python -m claimstab.cli run --spec specs/atlas_bv_demo.yml --out-dir output/quickstart --report
python -m claimstab.cli validate-evidence --json output/quickstart/claim_stability.json
```

Expected outputs:
- `output/quickstart/scores.csv`
- `output/quickstart/claim_stability.json`
- `output/quickstart/rq_summary.json`
- `output/quickstart/robustness_map.json`
- `output/quickstart/stability_report.html`

## Evaluation Tracks
Main paper tracks:
```bash
PYTHONPATH=. ./.venv/bin/python examples/exp_comprehensive_calibration.py
PYTHONPATH=. ./.venv/bin/python examples/exp_comprehensive_large.py
PYTHONPATH=. ./.venv/bin/python examples/exp_structural_compilation.py
```

Device-targeted extension:
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.multidevice_app --run all --suite standard --out-dir output/multidevice_full
```

External task plugin demo:
```bash
python -m claimstab.cli run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy
```

Generate your own external-task starter:
```bash
python -m claimstab.cli init-external-task --name my_problem --out-dir examples/my_problem_demo
```

Then run it:
```bash
python -m claimstab.cli run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
```

One-command artifact build (experiments + reports + figures):
```bash
make reproduce-paper
```

## Generate HTML Report
```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.scripts.generate_stability_report \
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
- `specs/atlas_bv_demo.yml` (small end-to-end publishable example)

Advanced direct pipeline entrypoint (secondary path):

```bash
PYTHONPATH=. ./.venv/bin/python -m claimstab.pipelines.claim_stability_app \
  --suite core \
  --spec examples/specs/claim_spec.yaml \
  --out-dir output/spec_run
```

Minimal publish path from a spec run:

```bash
python -m claimstab.cli validate-spec --spec specs/atlas_bv_demo.yml
python -m claimstab.cli run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_demo --report
python -m claimstab.cli publish-result --run-dir output/atlas_demo --atlas-root atlas --contributor your_name
```

Plot-enabled report:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcache XDG_CACHE_HOME=/tmp/cache \
PYTHONPATH=. ./.venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/quickstart/claim_stability.json \
  --out output/quickstart/stability_report_plots.html \
  --with-plots
```
