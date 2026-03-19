# Reproduction Contract

This contract defines the active reproduction scope for the `evaluation_v2` paper bundle.

## Scope

Main paper-facing reproduction now means:

- exact-scope battleground and calibration runs under `paper/experiments/specs/evaluation_v2/`
- derived paper summaries under `output/paper/evaluation_v2/derived_paper_evaluation/`
- publication-facing figures under `output/paper/evaluation_v2/pack/figures/`

The locked experiment matrix is documented in [Experiment Matrix](experiment_matrix.md).

## Supported Runtime Contract

Validated in the project `venv` with:

| Component | Contract |
|---|---|
| Python | `3.10` / `3.11` official artifact targets; newer local environments may work but are not the portability baseline |
| Qiskit core | `qiskit==2.2.3` |
| Aer | `qiskit-aer==0.17.2` |
| IBM runtime | `qiskit-ibm-runtime==0.45.1` |

## Required vs Optional

Required for the active paper bundle:

- `E1`, `E2`, `E3`, `E4`, `E5`, `S2`, and `QEC`

Supported with scope note:

- `S1` backend-conditioned transpile-only structural portability

Not part of the main contract:

- legacy `output/presentations/...` runs
- legacy `output/paper/artifact/...` pack generation
- replay-consistency reruns beyond the currently materialized bundle

## Canonical Commands

```bash
python paper/experiments/scripts/reproduce_evaluation_v2.py
python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2
python paper/experiments/scripts/generate_eval_v2_focus_figures.py --root output/paper/evaluation_v2
python -m claimstab.cli validate-evidence --json output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json
```

## Practical Note

`S1` should be interpreted as a controlled structural portability study, not as a full noisy-device claim-centric rerun. This is a scope note, not a reproduction failure.

## Validation Gates

```bash
./venv/bin/python -m pytest -q
./venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
./venv/bin/python -m mkdocs build --strict
```
