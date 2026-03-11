# Community Examples

This directory contains onboarding-first examples for external users.

## What Is Here

- `specs/atlas_bv_demo.yml`: smallest end-to-end runnable spec.
- `specs/claim_spec.yaml`: minimal claim-spec template.
- `specs/perturbation_spec.yaml`: perturbation template.
- `claim_stability_demo.py`: simple CLI demo runner.
- `atlas_bv_workflow.py`: run + publish to ClaimAtlas flow.
- `grover_distribution_demo.py`: distribution-claim demo.
- `multidevice_demo.py`: optional multidevice demo.
- `custom_task_demo/`: external task plugin example.
- `community_contrib_demo/`: community-style contributed problem example.

## Quick Start

```bash
python -m claimstab.cli validate-spec --spec examples/community/specs/atlas_bv_demo.yml
python -m claimstab.cli run --spec examples/community/specs/atlas_bv_demo.yml --out-dir output/examples/quickstart --report
```

Default output conventions:

- quickstart run: `output/examples/quickstart/`
- direct `claim_stability_demo.py`: `output/examples/claim_stability_demo/` (if `--out-dir` omitted)
- direct `multidevice_demo.py`: `output/examples/multidevice_demo/` (if `--out-dir` omitted)
- atlas workflow helper: `output/examples/atlas_bv_demo/`
- custom task demo: `output/examples/toy/`
- community-contributed portfolio demo: `output/examples/community_portfolio_demo/`

Use this folder if you are learning ClaimStab or contributing a new dataset/task.
