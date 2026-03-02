.PHONY: docs-serve docs-build figures

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

figures:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures --input-dir output/exp_comprehensive_large --also-calibration output/exp_comprehensive_calibration --output-dir figures
