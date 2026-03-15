.PHONY: venv install install-current precommit lint format test docs build clean

VENV ?= .venv
PYTHON ?= python3
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
VENV_PRE_COMMIT := $(VENV)/bin/pre-commit
VENV_RUFF := $(VENV)/bin/ruff
VENV_MYPY := $(VENV)/bin/mypy
VENV_PYTEST := $(VENV)/bin/pytest
VENV_MKDOCS := $(VENV)/bin/mkdocs
VENV_BUILD := $(VENV)/bin/python -m build

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"
	$(VENV_PRE_COMMIT) install

install-current:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"
	pre-commit install

precommit:
	$(VENV_PRE_COMMIT) run --all-files

lint:
	$(VENV_RUFF) check src tests
	$(VENV_RUFF) format --check src tests
	$(VENV_MYPY) src/{{ package_name }}

format:
	$(VENV_RUFF) check --fix src tests
	$(VENV_RUFF) format src tests

test:
	$(VENV_PYTEST) tests -v

docs:
	$(VENV_MKDOCS) build --strict

build:
	$(VENV_BUILD)

clean:
	rm -rf build dist .coverage .pytest_cache .mypy_cache .ruff_cache site
