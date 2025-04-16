# E2E Testing Scripts for FHIR Nudge

This folder contains scripts to help you run end-to-end (E2E) tests for the FHIR Nudge Proxy using Schemathesis and Flask.

## Scripts

### 1. `run_proxy.sh`
- **Purpose:** Launches the FHIR Nudge Flask proxy server on port 8888.
- **Usage:**
  ```bash
  ./run_proxy.sh
  ```
- **Details:**
  - Sets up the environment and runs the Flask app from the project root.
  - Make sure your dependencies are installed and the virtual environment is active (e.g., via Poetry).

### 2. `run_schemathesis.sh`
- **Purpose:** Runs Schemathesis against the running proxy server to validate API contract compliance and robustness.
- **Usage:**
  ```bash
  ./run_schemathesis.sh
  ```
- **Details:**
  - Assumes the proxy is already running on `http://localhost:8888`.
  - Loads the OpenAPI spec from `/openapi.yaml` and tests all documented endpoints.
  - Reports any mismatches or unexpected errors.

### 3. `run_e2e.sh`
- **Purpose:** Automates the full end-to-end test workflow: launches the Flask proxy, waits for it to be ready, runs all E2E tests (via `e2e_runner.py`), and shuts down the proxy afterward.
- **Usage:**
  ```bash
  ./run_e2e.sh
  ```
- **Details:**
  - Sets up environment variables and proxy port.
  - Waits for the server to be ready before running tests.
  - Cleans up the proxy process when done.
  - Useful for CI or for running all E2E tests in a single command.

## Typical Workflow

1. **Start the Proxy:**
   - In one terminal:
     ```bash
     ./run_proxy.sh
     ```
2. **Run Schemathesis:**
   - In another terminal:
     ```bash
     ./run_schemathesis.sh
     ```

## Notes & TODOs
- The current Schemathesis run will mostly exercise error cases unless you seed your backend with valid FHIR resources matching the examples in your OpenAPI spec.
- **TODO:** Add scripts or instructions for seeding the backend with known-good example resources to enable 200 OK test coverage.
- You can add parameter examples to your OpenAPI spec and use Schemathesis's `--examples-as-cases` option for targeted test cases.

## Requirements
- [Poetry](https://python-poetry.org/) for dependency management
- [Schemathesis](https://schemathesis.readthedocs.io/) (already included in dev dependencies)
- Python 3.10+

---
Feel free to extend these scripts or add new ones for additional E2E testing workflows!
