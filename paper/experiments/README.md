# Paper Experiments

This directory is the paper-only surface. It is intentionally separate from community onboarding.

## Active Bundles

- `specs/evaluation_v2/`
  - core paper evaluation
  - outputs under `output/paper/evaluation_v2/`
- `specs/evaluation_v3/`
  - strengthening studies `W1/W3/W4/W5`
  - outputs under `output/paper/evaluation_v3/`
- `specs/evaluation_v4/`
  - ICSE-strengthening analyses and hardware slices
  - outputs under `output/paper/evaluation_v4/`

Revision checklist:

- [ICSE_STRENGTHENING_TODO.md](./ICSE_STRENGTHENING_TODO.md)

## Core Entry Points

- `scripts/reproduce_evaluation_v2.py`
- `scripts/reproduce_evaluation_v3.py`
- `scripts/derive_icse_strengthening_v4.py`
- `scripts/run_real_hardware_slice_v1.py`

## Active Specs

### evaluation_v2

- `e1_maxcut_main.yml`
- `e2_ghz_structural.yml`
- `e3_bv_decision.yml`
- `e4_grover_distribution.yml`
- `s1_multidevice_portability.yml`
- `s2_boundary.yml`
- `qec_portability.yml`

### evaluation_v3

- `w1_vqe_pilot.yml`
- `w1_max2sat_second_family.yml`

### evaluation_v4

- `d1_bv_hardware_slice.yml`
- `d1_grover_hardware_slice.yml`
- `d1_vqe_hardware_slice.yml`

## Notes

- `S1` is a controlled structural portability study, not a full noisy-device rerun.
- `W4` should only report inter-rater agreement after real labels are placed under `paper/experiments/data/admissibility_v1/ratings/`.
