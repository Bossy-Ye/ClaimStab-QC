# Examples & Example Outputs

This page lists the examples that are aligned with the current repository state.

## Example A — Lightweight ClaimStab Demo

Command:

```bash
python examples/community/claim_stability_demo.py \
  --suite core \
  --sampling-mode random_k \
  --sample-size 8 \
  --sample-seed 1
```

Default output:

- `output/examples/claim_stability_demo/claim_stability.json`
- `output/examples/claim_stability_demo/stability_report.html`

## Example B — QEC Portability Demo

Command:

```bash
python -m claimstab.cli run \
  --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml \
  --out-dir output/examples/qec_pilot_demo \
  --report
```

What it evaluates:

- repetition-code-style decoder comparison
- `GlobalMajority > SingleReadout`
- metric: `logical_error_rate`

Representative outputs:

- `output/examples/qec_pilot_demo/claim_stability.json`
- `output/examples/qec_pilot_demo/stability_report.html`

## Example C — Backend-conditioned Structural Portability

Command:

```bash
python examples/community/multidevice_demo.py --run transpile_only --suite standard
```

Default output:

- `output/examples/multidevice_demo/`

This is a controlled structural portability demo, not a full noisy-device claim-centric rerun.

## Example D — Main Paper Battleground

Command:

```bash
python -m claimstab.cli run \
  --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml \
  --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main \
  --report
```

Representative outputs:

- `output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json`
- `output/paper/evaluation_v2/runs/E1_maxcut_main/rq_summary.json`
- `output/paper/evaluation_v2/runs/E1_maxcut_main/robustness_map.json`
- `output/paper/evaluation_v2/runs/E1_maxcut_main/stability_report.html`

## Example E — Paper-facing Derived Summaries

Command:

```bash
python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2
```

Representative outputs:

- `output/paper/evaluation_v2/derived_paper_evaluation/RQ1_necessity/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ2_semantics/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ3_diagnostics/`
- `output/paper/evaluation_v2/derived_paper_evaluation/RQ4_practicality/`

## Typical Artifacts

- `claim_stability.json`
- `rq_summary.json`
- `robustness_map.json`
- `scores.csv`
- `stability_report.html`

## Note on Older Examples

Some historical Atlas and external-task examples are still present in the repository for reference, but the examples on this page are the ones that match the current active workflow and output layout.
