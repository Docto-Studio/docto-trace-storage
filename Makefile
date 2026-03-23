.PHONY: install venv lint fix typecheck test run clean build banner

VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
BIN      := $(VENV)/bin

# Helper to print the banner using pyfiglet if available
BANNER = @$(PYTHON) -c "import pyfiglet; print(pyfiglet.figlet_format('DOCTO'))" 2>/dev/null || echo "DOCTO"

# Create the virtual environment
venv:
	$(BANNER)
	python -m venv $(VENV)
	$(PIP) install --upgrade pip -q

# Install the package in editable mode with dev extras (inside venv)
install: venv
	$(BANNER)
	$(PIP) install -e ".[dev]" -q

# Lint and format with ruff
lint:
	$(BANNER)
	$(BIN)/ruff check docto_trace tests
	$(BIN)/ruff format --check docto_trace tests

# Fix linting issues automatically
fix:
	$(BANNER)
	$(BIN)/ruff check --fix docto_trace tests
	$(BIN)/ruff format docto_trace tests

# Type-check
typecheck:
	$(BANNER)
	$(BIN)/mypy docto_trace

# Run tests (offline — no credentials needed)
test:
	$(BANNER)
	$(BIN)/pytest tests/ -v

# Quick smoke test — run the CLI
run:
	$(BIN)/docto-trace --help

# Build wheel and sdist
build:
	$(BANNER)
	$(BIN)/python -m build

# Remove all build and cache artifacts
clean:
	$(BANNER)
	rm -rf dist/ build/ *.egg-info .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
