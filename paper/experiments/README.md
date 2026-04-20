# Paper Experiments

This directory is the paper-only surface. It is intentionally separate from community onboarding.

It contains two different roles:

- historical experiment provenance and execution inputs
- work-tracking material for the current submission

It is not the canonical manuscript prose surface. For curated paper-facing
definitions, notes, figures, and tables, use:

- [`../presentation/icse_2027/`](../presentation/icse_2027/)

Current paper target:

- ClaimStab-QC is a software-engineering methodology paper instantiated in quantum software experiments.
- The core thesis is that empirical evaluation often validates outcomes, but not conclusions.

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

Current worklog:

- [ICSE 2027 sprint backlog](./backlog_icse_2027/README.md)
- archived strengthening checklist:
  - [`_archive_legacy/ICSE_STRENGTHENING_TODO.md`](./_archive_legacy/ICSE_STRENGTHENING_TODO.md)

## Core Entry Points

- `scripts/reproduce_evaluation_v2.py`
- `scripts/reproduce_evaluation_v3.py`
- `scripts/README.md`
- `scripts/export_rq1_metric_vs_claim.py`
- `scripts/export_rq1_baseline_comparison.py`
- `scripts/export_rq2_cross_family.py`
- `scripts/export_rq2_mismatch_patterns.py`
- `scripts/export_frozen_findings.py`
- `scripts/export_rq3_scope_transport.py`
- `scripts/export_rq3_exact_witness.py`
- `scripts/export_rq4_practicality.py`
- `scripts/export_supporting_bv_real_backend_check.py`
- `scripts/export_supporting_transpiler_claim_revalidation.py`
- `scripts/export_submission_artifact_index.py`
- `scripts/run_hardware_slice_ibm.py`
- `scripts/run_hardware_slice_iqm.py`
- `supporting_slices/bv_real_backend_check/README.md`
- `supporting_slices/transpiler_claim_revalidation/README.md`

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

- `d0_bv_iqm_fake_rehearsal.yml`
- `d0_bv_oracle_only_iqm_fake_rehearsal.yml`
- `d1_bv_hardware_slice.yml`
- `d1_bv_oracle_only_hardware_slice.yml`
- `d1_grover_hardware_slice.yml`
- `d1_vqe_hardware_slice.yml`

## Notes

- `S1` is a controlled structural portability study, not a full noisy-device rerun.
- `D0` is the local IQM fake-backend rehearsal. It should be run before any facade or real IQM/VTT execution.
- `W4` should only report inter-rater agreement after real labels are placed under `paper/experiments/data/admissibility_v1/ratings/`.
- canonical paper-facing exporters now use `export_rq*` naming rather than venue-coded names
- `supporting_slices/` is reserved for narrow appendix-level studies that do
  not alter the canonical main evidence surface
