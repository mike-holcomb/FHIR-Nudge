#!/bin/bash
# Always run from the project root
dcd="$(dirname "$0")/.."
cd "$dcd"
SCHEMA_URL="http://localhost:8888/openapi.yaml"
BASE_URL="http://localhost:8888"
poetry run schemathesis run $SCHEMA_URL --base-url=$BASE_URL
