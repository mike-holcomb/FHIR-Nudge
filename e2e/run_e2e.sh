#!/bin/bash

# Fail on error
set -e

# Set PYTHONPATH to project root for import resolution
echo "Setting PYTHONPATH to project root..."
export PYTHONPATH="$(dirname $(dirname $(realpath $0)))"

# Set FHIR_SERVER_URL if not already set
if [ -z "$FHIR_SERVER_URL" ]; then
  echo "FHIR_SERVER_URL not set. Using default: http://hapi.fhir.org/baseR4"
  export FHIR_SERVER_URL="http://hapi.fhir.org/baseR4"
fi

# Run the E2E tests
echo "Running E2E tests..."
poetry run python $(dirname $0)/e2e_runner.py
exit $?
