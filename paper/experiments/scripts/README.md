# Paper Experiment Scripts

This directory contains execution and export scripts for the paper evidence
surface. Filenames are grouped by purpose.

## Canonical paper-facing exporters

Use these when regenerating the current curated evidence bundle:

- `export_rq1_metric_vs_claim.py`
- `export_rq1_baseline_comparison.py`
- `export_rq2_cross_family.py`
- `export_rq2_mismatch_patterns.py`
- `export_frozen_findings.py`
- `export_rq3_scope_transport.py`
- `export_rq3_exact_witness.py`
- `export_rq4_practicality.py`
- `export_method_admissibility_summary.py`
- `export_supporting_bv_real_backend_check.py`
- `export_supporting_transpiler_claim_revalidation.py`
- `export_submission_artifact_index.py`

These are the preferred entry points for paper-facing datasets, tables, and
figures.

## Hardware and profile runners

- `run_hardware_slice_ibm.py`
- `run_hardware_slice_iqm.py`
- `run_fake_profile_transport.py`
- `run_supporting_transpiler_claim_revalidation.py`

These scripts execute supporting hardware or profile-conditioned studies. They
are not the main paper exporters.

## Historical rerun / legacy scripts

The remaining `derive_*`, `exp_*`, `generate_*`, and `summarize_*` scripts are
historical provenance or transitional utilities. They remain useful for
reproduction, but they are not the preferred naming pattern for new work.

## Naming rule

New scripts should be named for what they **do**:

- `export_...` for curated paper-facing outputs
- `run_...` for execution
- `reproduce_...` for historical bundle reruns

Do not add new venue-coded filenames such as `*_icse.py`.
