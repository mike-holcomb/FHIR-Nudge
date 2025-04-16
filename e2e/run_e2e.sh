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

PROXY_PORT=8888
PROXY_HOST=localhost
PROXY_URL="http://$PROXY_HOST:$PROXY_PORT"
echo "Starting Flask proxy on $PROXY_URL..."
poetry run flask --app fhir_nudge.app run --host $PROXY_HOST --port $PROXY_PORT &
PROXY_PID=$!

# Wait for the proxy to be ready (try up to 10 seconds)
for i in {1..10}; do
  if curl -s "$PROXY_URL/health" >/dev/null 2>&1 || curl -s "$PROXY_URL" >/dev/null 2>&1; then
    echo "Flask proxy is up!"
    break
  fi
  sleep 1
  if [ $i -eq 10 ]; then
    echo "Flask proxy did not start in time."
    kill $PROXY_PID
    exit 1
  fi
done

# Run the E2E tests
echo "Running E2E tests..."
poetry run python $(dirname $0)/e2e_runner.py
TEST_EXIT_CODE=$?

# Kill the Flask proxy
kill $PROXY_PID
wait $PROXY_PID 2>/dev/null

exit $TEST_EXIT_CODE
