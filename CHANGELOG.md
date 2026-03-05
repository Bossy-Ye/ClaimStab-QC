# Changelog

All notable changes to this project should be documented in this file.

## [Unreleased]

### Added
- Community docs: contributing, code of conduct, governance, and security policy.
- GitHub community templates (issues, PR template) and CI workflow.

### Changed
- README restructured for onboarding and reproducibility.
- Output conventions standardized around `output/`.
- Pipeline CSV writing path consolidated into `claimstab/pipelines/emit.py`; removed redundant `claimstab/io/writers.py`.
- Naive baseline reporting split into explicit dual-policy outputs:
  - `naive_baseline` (`legacy_strict_all`)
  - `naive_baseline_realistic` (`default_researcher_v1`)
- RQ summary, HTML report, and paper-figure naive views now support side-by-side policy comparison.
- Paper pack exporter now emits `tables/naive_policy_delta_snapshot.csv` for paper text/table extraction.
