# Reproduce

This page lists copy-paste commands for the current workflows in this repo.

## 1) Main paper track

```bash
claimstab validate-spec --spec specs/paper_main.yml
claimstab run --spec specs/paper_main.yml --out-dir output/paper_main --report
```

Expected artifacts:
- `output/paper_main/claim_stability.json`
- `output/paper_main/scores.csv`
- `output/paper_main/rq_summary.json`
- `output/paper_main/stability_report.html`

## 1.5) Structural compilation track (GHZ)

```bash
claimstab validate-spec --spec specs/paper_structural.yml
PYTHONPATH=. ./venv/bin/python examples/exp_structural_compilation.py --out-dir output/exp_structural_compilation
```

Expected artifacts:
- `output/exp_structural_compilation/claim_stability.json`
- `output/exp_structural_compilation/scores.csv`
- `output/exp_structural_compilation/rq_summary.json`

## 2) Device-aware extension

```bash
claimstab validate-spec --spec specs/paper_device.yml
claimstab run --spec specs/paper_device.yml --out-dir output/paper_device
```

Expected artifacts:
- `output/paper_device/...` (mode-dependent summaries, CSV/JSON)

## 3) Non-MaxCut BV + Atlas publication

```bash
claimstab validate-spec --spec specs/atlas_bv_demo.yml
claimstab run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_bv_demo --report
claimstab publish-result --run-dir output/atlas_bv_demo --atlas-root atlas --contributor your_name
claimstab validate-atlas --atlas-root atlas
```

Expected artifacts:
- `output/atlas_bv_demo/claim_stability.json`
- `atlas/submissions/<submission_id>/...`
- `atlas/index.json`

## 4) External user task starter

```bash
claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo
claimstab validate-spec --spec examples/my_problem_demo/spec_my_problem.yml
claimstab run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
claimstab publish-result --run-dir output/my_problem --atlas-root atlas --contributor your_name
```

## 5) Refresh website dataset page

```bash
claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

## 6) One-command paper reproduction

```bash
make reproduce-paper
```

This generates experiment outputs, HTML reports, paper figures, and a run manifest under `output/paper_artifact/`.

## 7) Trace / Cache / Replay workflow

See [Trace Cache Replay](trace_cache_replay.md) for copy-paste commands for both:
- `examples/claim_stability_demo.py`
- `examples/multidevice_demo.py`

## Runtime Expectations
- `core` smoke runs: short.
- `standard`/`large` comprehensive runs: moderate to long.
- multi-device transpile-only: moderate (depends on number of devices and sampled configs).
- noisy simulation: longer and environment dependent.
