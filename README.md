# FHIR Nudge

**FHIR Proxy for LLM Applications with Enhanced Error Feedback**

This project implements a Flask-based proxy server that sits between a HAPI FHIR server and an LLM (Large Language Model) application. Its primary goal is to enhance the experience of querying a FHIR server by providing richer error messages and actionable guidance when client queries are incomplete, ambiguous, or contain common errors.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Setting and Context](#setting-and-context)
- [Goals and Objectives](#goals-and-objectives)
- [High-Level Approach](#high-level-approach)
- [Key Techniques and Components](#key-techniques-and-components)
  - [Structured Retrieval via CapabilityStatement](#structured-retrieval-via-capabilitystatement)
  - [Limited Prevalidation of Search Parameters](#limited-prevalidation-of-search-parameters)
  - [Soft Error Handling for Empty Results](#soft-error-handling-for-empty-results)
  - [Code and Value Validation (e.g., LOINC)](#code-and-value-validation-eg-loinc)
- [Usage and Deployment](#usage-and-deployment)
- [Future Work](#future-work)
- [License](#license)
- [Documentation](#documentation)
- [Client Usage](#client-usage)
- [Error Handling & AIX Error Schema](#error-handling--aix-error-schema)
- [OpenAPI Specification, Testing, and Coverage](#openapi-specification-testing-and-coverage)

---

## Project Overview

This project delivers a lightweight proxy that transforms and augments requests between an LLM application and a HAPI FHIR server. It exposes two GET endpoints:

- **`/readResource/<resource>/<resource_id>`**: For retrieving individual FHIR resources.
- **`/searchResource/<resource>`**: For conducting searches using query parameters.

When errors occur—whether due to misspelled parameters or coding errors like incorrect LOINC codes—the proxy enriches the error messages with context, suggestions, and sometimes even a reference subdocument of supported search parameters extracted dynamically from the FHIR server.

---

## Setting and Context

Modern healthcare systems often rely on FHIR (Fast Healthcare Interoperability Resources) as a standard for exchanging electronic health records. FHIR servers like HAPI expose a rich API surface but come with steep learning curves and complex error messages. Meanwhile, Large Language Models are increasingly used to interact with these systems. However, LLMs (and their users) might submit incorrect or ambiguous queries, leading to empty or unhelpful responses.

In this context, our proxy:

- **Bridges the gap** between LLM-driven queries and the rigid validation behavior of a FHIR server.
- **Enhances error feedback** to help clients iteratively improve their queries.
- **Utilizes dynamic metadata** from the FHIR server (via the CapabilityStatement) to guide valid query construction.

---

## Goals and Objectives

- **Enhance User Experience:** Provide clear, actionable error messages when queries fail.
- **Dynamic Adaptability:** Automatically obtain the FHIR server’s supported search parameters to avoid outdated hard-coded validations.
- **Minimize Redundancy:** Avoid full duplication of the FHIR server’s validation while catching common errors early.
- **Support for Coded Values:** Offer structured guidance on proper usage of coded fields (e.g., LOINC for observations).
- **Facilitate Client Learning:** Equip LLMs and human users with the information needed to refine their search parameters for optimal results.

---

## High-Level Approach

1. **Dynamic Retrieval of Search Metadata:**
   - On startup, the proxy retrieves the FHIR server’s CapabilityStatement from the `/metadata` endpoint.
   - It parses this document to create a dynamic index mapping resource types to their supported search parameters.

2. **Limited Prevalidation:**
   - Before forwarding queries to the FHIR server, the proxy performs lightweight prevalidation.
   - It checks that the provided query parameter names exist in the dynamic index.
   - For common mistakes (e.g., typos), it suggests corrections based on fuzzy matching.

3. **Soft Error Handling:**
   - Even if a query passes prevalidation, a search returning an empty result set is interpreted as a “soft error.”
   - The proxy then augments the response with a warning and includes the supported search parameters subdocument to help the client revise its query.

4. **Code and Value Validation:**
   - For resources that use coded values (e.g., LOINC codes in Observations), the proxy validates that the supplied code exists in a dynamically built index (from a ValueSet or CodeSystem).
   - Invalid codes trigger immediate feedback with suggestions, rather than returning an empty search result.

---

## Key Techniques and Components

### Structured Retrieval via CapabilityStatement

- **Dynamic Indexing:**  
  The proxy loads the FHIR server's CapabilityStatement at startup and constructs a knowledge base that maps each resource (e.g., Patient, Observation) to its allowed search parameters.
  
- **Up-to-Date Metadata:**  
  Since the CapabilityStatement reflects the server’s current configuration, the proxy’s validations and suggestions always use authoritative, real-time information.

### Limited Prevalidation of Search Parameters

- **Early Error Detection:**  
  By prevalidating query parameters against the CapabilityStatement-derived index, the proxy can immediately catch typos (e.g., “nme” instead of “name”) or unsupported parameters.
  
- **Fuzzy Matching for Corrections:**  
  Using tools like Python’s `difflib.get_close_matches`, the proxy suggests correct parameter names, reducing the back-and-forth of trial-and-error.

### Soft Error Handling for Empty Results

- **Guiding Adjustments:**  
  When a search yields an empty result set, instead of returning an unhelpful empty bundle, the proxy attaches a soft error message suggesting the user review or modify their query.
  
- **Reference Documentation:**  
  It embeds the applicable supported search parameters (from the CapabilityStatement) directly in the response, enabling quick reference and adjustment.

### Code and Value Validation (e.g., LOINC)

- **Targeted Validation:**  
  For coded fields, such as an Observation's “code” parameter, the proxy uses an index of allowed codes (possibly derived from an external ValueSet or CodeSystem) to verify client inputs.
  
- **Actionable Feedback:**  
  If the client submits an incorrect LOINC code, the proxy returns an error with suggestions or a list of allowed codes, guiding the client toward correction.

---

## Error Handling & AIX Error Schema

FHIR Nudge uses a standardized, actionable error handling system designed for both LLMs and humans. All error responses conform to the [AIX Error Schema](docs/AIX_ERROR_SCHEMA.md). The contract is as follows:

- **App code is responsible for providing all actionable context** (diagnostics, resource type, resource ID, etc.) to the error renderer.
- **The error renderer formats and standardizes** the response, using templates for friendly messages and next steps, but does not invent diagnostics.
- **Diagnostics are always explicit and actionable**—for example, if a resource type is not supported, diagnostics will say so and list supported types. If a typo is detected, diagnostics will suggest corrections.
- **No legacy or top-level ad-hoc fields** like `supported_types` or `did_you_mean`—all context is in the `issues` array in the response.
- **Details field:** Each issue may include a `details` property for structured, machine-friendly context alongside diagnostics.

See [docs/ERROR_HANDLING_GUIDELINES.md](docs/ERROR_HANDLING_GUIDELINES.md) for implementation details and [docs/AIX_ERROR_SCHEMA.md](docs/AIX_ERROR_SCHEMA.md) for the schema.

---

## OpenAPI Specification, Testing, and Coverage

### OpenAPI Support
- The project includes a hand-authored OpenAPI 3.0 specification (`openapi.yaml`) describing all public API endpoints, parameters, request/response schemas, and error formats (including the AIX error schema).
- The spec is served at `/openapi.yaml` by the Flask app for easy access by humans, LLMs, and tools.
- The spec is richly documented with descriptions and examples to maximize clarity and LLM-friendliness.

### Automated OpenAPI Validation
- The test suite includes `tests/test_openapi_spec.py`, which uses `openapi-spec-validator` to ensure the OpenAPI spec is always valid and standards-compliant.
- Run all tests (including spec validation) with:
  ```bash
  poetry run pytest
  ```

### Contract Testing with Schemathesis
- End-to-end (E2E) testing is supported via [Schemathesis](https://schemathesis.readthedocs.io/), which generates and runs property-based tests against the live API based on the OpenAPI spec.
- Scripts in the `e2e/` folder:
  - `run_proxy.sh`: Starts the Flask proxy server on port 8888.
  - `run_schemathesis.sh`: Runs Schemathesis against the running proxy.
  - `run_e2e.sh`: Automates the full E2E workflow (starts proxy, runs tests, shuts down proxy).
- See `e2e/README.md` for complete usage instructions.

### Coverage Caveats & Improving Test Cases
- By default, Schemathesis generates random and edge-case inputs, so most responses are 4xx errors unless the backend is seeded with valid FHIR resources.
- **TODO:** Add scripts or instructions for seeding the backend with known-good example resources to enable 200 OK test coverage, and add parameter examples to the OpenAPI spec for targeted testing (`--examples-as-cases`).

### How to Update the OpenAPI Spec
1. Edit `openapi.yaml` to reflect any new endpoints, parameters, or changes in error handling.
2. Add rich descriptions and examples for new endpoints and schemas.
3. Run `poetry run pytest` to validate the spec and ensure all tests pass.
4. Optionally, run E2E tests:
   ```bash
   cd e2e
   ./run_proxy.sh   # in one terminal
   ./run_schemathesis.sh   # in another terminal
   ```
5. For full contract coverage, ensure your backend FHIR server contains resources matching the examples in your spec.

---

## Usage and Deployment

### Configuration

Before running the proxy, create a `.env` file in the project root with the following content:

```
FHIR_SERVER_URL=http://your-fhir-server-url/fhir
```

Replace the value with your actual FHIR server endpoint. This keeps sensitive configuration out of your codebase.

### Installation (Poetry-based)

1. **Clone the Repository:**

   ```bash
   git clone <repository-url>
   cd fhir-nudge
   ```

2. **Install Dependencies with Poetry:**

   ```bash
   poetry install
   ```

### Running the Proxy

Start the proxy server using Poetry:

```bash
poetry run python app.py
```

The proxy will start on [http://localhost:8888](http://localhost:8888).

### Endpoints

- **`/readResource/<resource>/<resource_id>`**
  - **Description:** Retrieves an individual FHIR resource.
  - **Example:** `GET /readResource/Patient/123`
  
- **`/searchResource/<resource>`**
  - **Description:** Conducts a search on a specified FHIR resource, with query parameters forwarded to the FHIR server.
  - **Example:** `GET /searchResource/Patient?name=john%20doe`

For Python clients, see [docs/CLIENT.md](docs/CLIENT.md) for usage examples via `FhirNudgeClient`.

If errors are encountered—such as unrecognized search parameters or invalid coded values—the proxy will respond with enhanced error messages and suggestions, including a reference subdocument outlining supported parameters for the queried resource.

---

## Documentation

- See [docs/AIX_ERROR_SCHEMA.md](docs/AIX_ERROR_SCHEMA.md) for a detailed description of the AI Experience (AIX) error schema used in FHIR Nudge error responses. This schema is designed to make FHIR errors more actionable and understandable for both humans and AI tools.
- See [docs/CLIENT.md](docs/CLIENT.md) for the Python client usage guide.

---

## Client Usage

See [docs/CLIENT.md](docs/CLIENT.md) for the Python client usage guide.

---

## Future Work

- **Caching and Refreshing Metadata:**  
  Implement periodic updates of the CapabilityStatement and ValueSet indexes to ensure real-time accuracy.

- **Enhanced Transformation Logic:**  
  Develop smarter query transformation strategies (e.g., splitting composite full-name strings into `given` and `family`).

- **Advanced Error Analytics:**  
  Integrate logging and analytics for monitoring how clients interact with the proxy and where errors are most frequently occurring.

- **Broader Code Validation:**  
  Expand the code validation beyond LOINC to include other coded systems as needed.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

By leveraging the server’s CapabilityStatement, limited prevalidation, and structured retrieval techniques, this proxy not only forwards requests to a HAPI FHIR server but also equips clients (or LLMs) with the guidance necessary to construct valid queries, ultimately leading to a more robust and user-friendly integration.