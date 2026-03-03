.PHONY: docs-serve docs-build figures ecosystem-validate

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

figures:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures --input-dir output/exp_comprehensive_large --also-calibration output/exp_comprehensive_calibration --output-dir figures

ecosystem-validate:
	PYTHONPATH=. ./venv/bin/python -m claimstab.cli validate-ecosystem --root ecosystem
