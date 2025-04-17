# FHIR Nudge Client Usage

This document describes how to use the `FhirNudgeClient` to interact with the FHIR Nudge proxy server.

## Overview

The `FhirNudgeClient` provides a simple Python wrapper over HTTP calls to the proxy, exposing:

- `read_resource(resource_type, resource_id)` — fetch a single FHIR resource.
- `search_resource(resource_type, params)` — perform a search query and return a FHIR Bundle.

Under the hood, it uses the `requests` library and raises exceptions for non-2xx responses or timeouts.

## Installation

Ensure `requests` is installed in your environment:

```bash
pip install requests
```

Then import the client:

```python
from fhir_nudge.client import FhirNudgeClient
```

## Initialization

```python
# Point to your running proxy (default timeout = 10s)
client = FhirNudgeClient("http://localhost:8888", timeout=5)
```

## Methods

### read_resource(resource_type, resource_id)
Fetches a single FHIR resource by its type and ID.

**Parameters**:
- `resource_type` (str): FHIR resource type (e.g., `"Patient"`).
- `resource_id` (str): Identifier of the resource.

**Returns**:
- A Python `dict` representing the JSON resource.

**Raises**:
- `requests.exceptions.HTTPError` if the server returns a non-2xx status.
- `requests.exceptions.Timeout` if the request times out.

**Example**:
```python
patient = client.read_resource("Patient", "123")
print(patient["resourceType"])  # "Patient"
```

### search_resource(resource_type, params)
Performs a search query against the FHIR server and returns a Bundle.

**Parameters**:
- `resource_type` (str): FHIR resource type to search (e.g., `"Observation"`).
- `params` (dict): Dictionary of search parameters (e.g., `{"code": "1234-5"}`).

**Returns**:
- A Python `dict` representing a FHIR Bundle resource.

**Raises**:
- `requests.exceptions.HTTPError` on non-2xx status.
- `requests.exceptions.Timeout` if the request times out.

**Example**:
```python
bundle = client.search_resource("Observation", {"code": "29463-7"})
print(bundle["entry"][0]["resource"]["resourceType"])  # "Observation"
```

## Future Methods

The client also plans to support:

- `create_resource(resource_type, resource)`
- `update_resource(resource_type, resource_id, resource)`
- `delete_resource(resource_type, resource_id)`
- `get_capability_statement()`

These will be added in future releases.
