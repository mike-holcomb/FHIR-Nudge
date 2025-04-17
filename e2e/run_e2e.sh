#!/bin/bash

# Fail on error
set -e

# Set PYTHONPATH to project root for import resolution
echo "Setting PYTHONPATH to project root..."
export PYTHONPATH="$(dirname $(dirname $(realpath $0)))"

# Run the E2E tests
echo "Running E2E tests..."
poetry run python $(dirname $0)/e2e_runner.py
exit $?
