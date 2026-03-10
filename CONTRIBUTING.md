# Contributing to ClaimStab-QC

Thanks for contributing. This project values reproducibility, clarity, and test-backed changes.

## Development Setup
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Optional extras:
```bash
python -m pip install -e ".[aer,ibm,dev]"
```

## Contribution Workflow
1. Fork and create a branch from `main`.
2. Make focused changes with tests.
3. Run the full test suite locally.
4. Open a pull request using the template.

## Quality Bar
- Keep behavior backward compatible unless clearly documented.
- Add or update tests for every logic change.
- Keep CLI help text and README usage examples in sync with code.
- Prefer deterministic outputs and explicit seeds in experiments.
- Follow `docs/compatibility_contract.md` for stable interface constraints.

## Local Validation
```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
./.venv/bin/python -m mkdocs build --strict
```

For reporting changes, run:
```bash
./.venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/claim_stability.json \
  --out output/stability_report.html
```

For public results dataset submissions, run:
```bash
python -m claimstab.cli publish-result --run-dir output/paper_main --atlas-root atlas --contributor your_name
python -m claimstab.cli validate-atlas --atlas-root atlas
python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

## Commit Style
Use concise commit messages that state the intent:
- `feat: add device-aware noisy simulation mode`
- `fix: preserve baseline config under random sampling`
- `docs: restructure README community section`

## Need Help?
Open a discussion/issue with:
- expected behavior,
- observed behavior,
- minimal command to reproduce,
- environment details (Python, OS, key package versions).
