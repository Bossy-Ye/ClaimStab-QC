.PHONY: docs-serve docs-build figures atlas-validate dataset-registry reproduce-paper

PYTHON ?= python3
MKDOCS_PY := $(if $(wildcard ./venv/bin/python),./venv/bin/python,$(PYTHON))

docs-serve:
	$(MKDOCS_PY) -m mkdocs serve

docs-build:
	$(MKDOCS_PY) -m mkdocs build

figures:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures --input-dir output/exp_comprehensive_large --also-calibration output/exp_comprehensive_calibration --output-dir figures

atlas-validate:
	PYTHONPATH=. ./venv/bin/python -m claimstab.cli validate-atlas --atlas-root atlas

dataset-registry:
	PYTHONPATH=. ./venv/bin/python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md

reproduce-paper:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.reproduce_paper --out-root output/paper_artifact --backend-engine basic
