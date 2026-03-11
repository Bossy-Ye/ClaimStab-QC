# Reproduction Contract

This contract defines what is required to reproduce the **main paper evaluation** versus optional extension tracks.
The locked experiment matrix is documented in `docs/experiment_matrix.md`.

## Scope
- **Main paper evaluation**: comprehensive claim-stability experiments from `paper/experiments/scripts/exp_comprehensive_*.py`.
- **Structural benchmark track**: `paper/experiments/scripts/exp_structural_compilation.py` (GHZ compilation claims).
- **Device-aware extension**: `claimstab/pipelines/multidevice_app.py` (transpile-only + optional noisy simulation).

## Supported Runtime Contract

Checked in the project `venv` on **March 2, 2026**.

| Component | Contract |
|---|---|
| Python | `3.10` / `3.11` officially supported for artifact runs |
| Qiskit core | `qiskit==2.2.3` validated |
| Aer | optional for main track, required for noisy simulation (`qiskit-aer==0.17.2` validated) |
| IBM runtime | optional, needed for IBM fake backend device profiles (`qiskit-ibm-runtime==0.45.1` validated) |

## Required vs Optional
- `examples/community/claim_stability_demo.py`: required for community-size demo reproduction.
- `examples/community/multidevice_demo.py --run transpile_only`: optional extension, reproducible without real hardware.
- `examples/community/multidevice_demo.py --run noisy_sim`: optional extension; may be environment-sensitive and does **not** block main-result reproducibility.

## Practical Note
Python 3.13 may show native Aer instability for noisy simulation in some environments; this does not affect the main-paper track.

## Canonical Install
```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[aer,ibm]"
```

## Canonical Main Commands
```bash
PYTHONPATH=. ./.venv/bin/python paper/experiments/scripts/exp_comprehensive_calibration.py
PYTHONPATH=. ./.venv/bin/python paper/experiments/scripts/exp_comprehensive_large.py
PYTHONPATH=. ./.venv/bin/python paper/experiments/scripts/exp_structural_compilation.py
python -m claimstab.cli validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json
make reproduce-paper
```
