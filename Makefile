.PHONY: docs-serve docs-build figures atlas-validate dataset-registry reproduce-paper gen-catalog clean-local

PYTHON ?= python3
MKDOCS_PY := $(if $(wildcard ./venv/bin/python),./venv/bin/python,$(PYTHON))

docs-serve:
	$(MKDOCS_PY) -m mkdocs serve

docs-build:
	$(MKDOCS_PY) -m mkdocs build

gen-catalog:
	PYTHONPATH=. $(MKDOCS_PY) -m claimstab.scripts.generate_implementation_catalog --out _archive_legacy/docs/generated/implementation_catalog.md

figures:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures --input-dir output/paper_artifact/large/maxcut_ranking --also-calibration output/paper_artifact/calibration/maxcut_ranking --output-dir output/paper_artifact/figures/main

atlas-validate:
	PYTHONPATH=. ./venv/bin/python -m claimstab.cli validate-atlas --atlas-root atlas

dataset-registry:
	PYTHONPATH=. ./venv/bin/python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md

reproduce-paper:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.reproduce_paper --out-root output/paper_artifact --backend-engine basic

clean-local:
	PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.clean_workspace --root . --apply
