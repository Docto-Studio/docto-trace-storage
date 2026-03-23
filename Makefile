.PHONY: install venv lint fix typecheck test run clean build

VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
BIN      := $(VENV)/bin

# Create the virtual environment
venv:
	python -m venv $(VENV)
	$(PIP) install --upgrade pip -q

# Install the package in editable mode with dev extras (inside venv)
install: venv
	$(PIP) install -e ".[dev]" -q

# Lint and format with ruff
lint:
	$(BIN)/ruff check docto_trace tests
	$(BIN)/ruff format --check docto_trace tests

# Fix linting issues automatically
fix:
	$(BIN)/ruff check --fix docto_trace tests
	$(BIN)/ruff format docto_trace tests

# Type-check
typecheck:
	$(BIN)/mypy docto_trace

# Run tests (offline — no credentials needed)
test:
	$(BIN)/pytest tests/ -v

# Quick smoke test — run the CLI
run:
	$(BIN)/docto-trace --help

# Build wheel and sdist
build:
	$(BIN)/python -m build

# Remove all build and cache artifacts
clean:
	rm -rf dist/ build/ *.egg-info .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
