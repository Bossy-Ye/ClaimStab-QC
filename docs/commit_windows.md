# Commit Windows

This document defines the intended commit boundaries for the current repo
convergence pass. The goal is to avoid mixing structure cleanup, renamed script
entry points, and manuscript-facing additions into a single noisy commit.

## Window A: Structure and hygiene

Purpose:

- clarify repository surfaces
- reduce venue leakage outside the submission subtree
- remove or isolate local-only clutter

Safe contents:

- `.gitignore`
- top-level and paper-surface `README.md` files that clarify repository roles
- `docs/repo_layout.md`
- `docs/commit_windows.md`
- `paper/experiments/_archive_legacy/README.md`
- updates that explicitly mark backlog as work tracking rather than manuscript prose
- updates that explicitly mark `paper/presentation/icse_2027/` as the
  manuscript-facing surface

Exact path set for this repository at the time of writing:

- `.gitignore`
- `README.md`
- `docs/commit_windows.md`
- `docs/repo_layout.md`
- `paper/experiments/_archive_legacy/ICSE_STRENGTHENING_TODO.md`
- `paper/experiments/_archive_legacy/README.md`
- `paper/experiments/backlog_icse_2027/README.md`
- `paper/presentation/README.md`
- `paper/presentation/icse_2027/README.md`
- `paper/presentation/icse_2027/definitions/README.md`
- `paper/presentation/icse_2027/notes/README.md`

Do not mix into this commit:

- renamed script entry points
- new experiment specs
- new hardware notes
- exploratory pilots

## Window B: Canonical script naming and minimal hardware surface

Purpose:

- replace venue-coded script names with purpose-coded names
- keep the minimal hardware reality-check additions in a single coherent unit

Safe contents:

- renamed `export_rq*` scripts
- renamed hardware/profile runners
- references updated to those renamed scripts
- `d0_bv_oracle_only_iqm_fake_rehearsal.yml`
- `d1_bv_oracle_only_hardware_slice.yml`
- `paper/presentation/icse_2027/notes/hardware_reality_check_note.md`

Exact path set for this repository at the time of writing:

- `docs/design_your_own_case.md`
- `paper/experiments/README.md`
- `paper/experiments/backlog_icse_2027/02_E1_METRIC_VS_CLAIM.md`
- `paper/experiments/backlog_icse_2027/03_E2_BASELINE_COMPARISON.md`
- `paper/experiments/backlog_icse_2027/06_E5_CROSS_FAMILY.md`
- `paper/experiments/backlog_icse_2027/07_E6_REAL_HARDWARE.md`
- `paper/experiments/backlog_icse_2027/10_PAPER_FRAMING.md`
- `paper/experiments/scripts/README.md`
- `paper/experiments/scripts/export_rq1_baseline_comparison.py`
- `paper/experiments/scripts/export_rq1_metric_vs_claim.py`
- `paper/experiments/scripts/export_rq2_cross_family.py`
- `paper/experiments/scripts/export_rq3_exact_witness.py`
- `paper/experiments/scripts/export_rq3_scope_transport.py`
- `paper/experiments/scripts/export_rq4_practicality.py`
- `paper/experiments/scripts/run_fake_profile_transport.py`
- `paper/experiments/scripts/run_hardware_slice_ibm.py`
- `paper/experiments/scripts/run_hardware_slice_iqm.py`
- `paper/experiments/specs/evaluation_v4/d0_bv_oracle_only_iqm_fake_rehearsal.yml`
- `paper/experiments/specs/evaluation_v4/d1_bv_oracle_only_hardware_slice.yml`
- `paper/presentation/icse_2027/notes/hardware_reality_check_note.md`

Do not mix into this commit:

- broad prose rewrites
- exploratory hardware preflight scratch assets
- unrelated pilot branches

## Local-only and archive-only material

The following should remain outside the committed repo surface unless they are
reintroduced deliberately through a separate review:

- `.local_archive/`
- office documents
- exploratory pilots not connected to the current paper surface
- hardware preflight scratch documents
- unreviewed manuscript drafts

## Staging rule

Do not use `git add .` for this cleanup pass.

Stage files explicitly by window so that:

1. the repo-structure commit is independently reviewable, and
2. the script/hardware-surface commit is independently reviewable.
