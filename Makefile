.PHONY: install lint test run clean

# Install the package in editable mode with dev extras
install:
	pip install -e ".[dev]"

# Lint and format with ruff
lint:
	ruff check docto_trace tests
	ruff format --check docto_trace tests

# Fix linting issues automatically
fix:
	ruff check --fix docto_trace tests
	ruff format docto_trace tests

# Type-check
typecheck:
	mypy docto_trace

# Run tests
test:
	pytest tests/ -v

# Quick smoke test — run the CLI
run:
	docto-trace --help

# Remove build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
