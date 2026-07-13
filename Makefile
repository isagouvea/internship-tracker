PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
APP := PYTHONPATH=src $(BIN)/python -m internship_tracker.cli

.PHONY: setup init update smoke public-site preview report privacy-check test stats

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e '.[dev]'

init:
	$(APP) init

update:
	$(APP) update
	$(APP) report
	$(APP) public-site
	$(APP) privacy-check

smoke:
	$(APP) update --smoke --limit 5

public-site:
	$(APP) public-site

preview:
	$(BIN)/python scripts/preview.py

report:
	$(APP) report

privacy-check:
	$(APP) privacy-check

test:
	PYTHONPATH=src $(BIN)/pytest -q

stats:
	$(APP) stats
