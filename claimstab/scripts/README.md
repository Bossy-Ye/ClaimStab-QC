# Scripts Layout

`claimstab/scripts/` contains thin, composable command entrypoints.

Canonical entrypoints:
- `reproduce_paper.py`: full experiment+report+figure reproduction bundle.
- `export_paper_pack.py`: package an existing run family into `tables/`, `figures/`, and a reproducibility manifest.
- `make_paper_figures.py`: generate paper-ready figures from run outputs.
- `generate_stability_report.py`: render HTML report from `claim_stability.json`.
- `generate_implementation_catalog.py`: regenerate docs implementation catalog.
- `check_expected.py`: lightweight output expectation check used by docs/workflows.
- `clean_workspace.py`: delete local caches/generated scratch artifacts (safe for regeneration).

Guidelines:
- Prefer calling reusable library modules from scripts (avoid embedding pipeline logic here).
- Keep script outputs deterministic and include manifest/provenance where possible.
- Use `output/` for local/generated artifacts; do not commit ad-hoc generated snapshots.
