.PHONY: test syntax health index lint quality acceptance graph plugin

PYTHON ?= python3

test: syntax health index lint quality acceptance graph plugin

syntax:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile tools/*.py

health:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/health.py

index:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/build_index.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/build_index.py --check

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/lint_links.py --write-cache

quality:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/audit_wiki_quality.py --write-cache

acceptance:
	PYTHONDONTWRITEBYTECODE=1 tests/acceptance.sh

graph:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/export_graph.py --html

plugin:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/install_plugin.py --check
