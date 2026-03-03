# Contributing to ClaimStab-QC

Thanks for contributing. This project values reproducibility, clarity, and test-backed changes.

## Development Setup
```bash
python -m venv venv
source venv/bin/activate
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

## Local Validation
```bash
PYTHONPATH=. ./venv/bin/python -m pytest -q
```

For reporting changes, run:
```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/claim_stability.json \
  --out output/stability_report.html
```

For ecosystem contributions (tasks/methods/suites/results), run:
```bash
claimstab validate-ecosystem --root ecosystem
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
