#!/bin/bash
# Always run from the project root
dcd="$(dirname "$0")/.."
cd "$dcd"
export FLASK_APP=fhir_nudge.app
export FLASK_ENV=development
poetry run flask run --port=8888
