#!/bin/bash
# Run unit tests for all agents

set -e

cd "$(dirname "$0")/.."

# Install test dependencies
pip install -r shared/requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Set PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Run tests with coverage
pytest tests/ \
    -v \
    --cov=shared \
    --cov=orchestrator \
    --cov=agents \
    --cov-report=term-missing \
    --cov-report=html:coverage_report \
    --cov-fail-under=70

echo "Tests completed successfully!"
