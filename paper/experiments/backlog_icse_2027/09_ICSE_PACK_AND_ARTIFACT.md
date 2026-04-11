# 09 ICSE Pack and Artifact

## Goal

Build a compact, verifiable paper-facing artifact surface that reviewers can navigate without understanding the project’s full history.

## Placement Rule

This task owns the material that is too detailed for the ICSE paper PDF but still
necessary for transparency, verifiability, and reproducibility.

It should contain:

- detailed breakdown tables that are not promoted into the paper PDF
- reproduction commands for all canonical figures and tables
- exact/approx diagnostics notes
- minimal audit notes and hardware notes

It should not be used as a dumping ground for:

- abandoned historical bundles
- exploratory visuals
- duplicate copies of canonical paper figures without a reproducibility reason

## Outputs

- unified `icse_pack/` directory
- compact result index
- figure-generation commands
- exact/approx diagnostics note
- reproducibility README

## Acceptance Criteria

- [ ] A reviewer can find final figures, final tables, and final summary files from one root.
- [ ] The boundary between main-paper content, appendix content, and artifact-only content is explicit.
- [ ] Exact/approx diagnostic status is stated explicitly.
- [ ] Reproduction commands are short and current.
- [ ] The artifact surface does not expose unnecessary historical bundles as if they were the final paper pack.

## Dependencies

- [08_FIGURES_AND_TABLES.md](./08_FIGURES_AND_TABLES.md)

## Status

- [ ] Not started
- [ ] In progress
- [ ] Done

## Notes

This task is about verifiability and transparency, not about adding more experiments.
