from flask import Flask, request, jsonify, Response, make_response, abort, send_file
import requests
import difflib
from dotenv import load_dotenv
import os
import re
from fhir_nudge.error_renderer import render_error

app = Flask(__name__)

load_dotenv()
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")
FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-\.]{1,64}$")

# TODO: Refactor capability_index (knowledgebase) into its own class for better testability and maintainability.

def load_capability_statement():
    """
    Fetches the CapabilityStatement from the FHIR server and builds a mapping:
    { resource_type: list([param_obj1, ...]), ... }
    Returns an empty dict on error.
    """
    try:
        metadata_url = f"{FHIR_SERVER_URL}/metadata"
        resp = requests.get(metadata_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        index = {}
        # Parse the CapabilityStatement for resource search params
        for rest in data.get("rest", []):
            for resource in rest.get("resource", []):
                resource_type = resource.get("type")
                param_objs = []
                for param in resource.get("searchParam", []):
                    param_obj = {
                        "name": param.get("name"),
                        "type": param.get("type"),
                        "documentation": param.get("documentation"),
                        "example": param.get("example"),
                    }
                    param_objs.append(param_obj)
                index[resource_type] = param_objs
        return index
    except Exception as e:
        print("\n[ FATAL ERROR: Failed to load FHIR CapabilityStatement ]\n" + "-"*60)
        print(f"Exception: {e}\n")
        print(f"FHIR_SERVER_URL: {FHIR_SERVER_URL}")
        print("\nTroubleshooting suggestions:")
        print("  - Ensure the FHIR_SERVER_URL is correct and reachable.")
        print("  - Check your network connection.")
        print("  - Make sure the FHIR server is running and accessible from this machine.")
        print("  - If the server requires authentication, confirm credentials and headers.")
        print("  - Try opening {FHIR_SERVER_URL}/metadata in your browser or with curl.")
        print("\nThe proxy cannot start without a valid CapabilityStatement. Exiting.\n")
        import sys
        sys.exit(1)

def filter_headers(headers):
    # Normalize header keys to lower-case for case-insensitive filtering
    excluded = {
        'transfer-encoding', 'content-encoding', 'content-length', 'connection',
        'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'upgrade'
    }
    return {k: v for k, v in headers.items() if k.lower() not in excluded}

capability_index = None

def get_capability_index():
    global capability_index
    if capability_index is None:
        capability_index = load_capability_statement()
    return capability_index

def _prevalidate_search_resource(resource: str, query_params: dict):
    """
    Perform lightweight prevalidation of a searchResource request.
    Returns (is_valid, error_response) where:
      - is_valid: bool, True if request is valid enough to forward
      - error_response: Flask response if invalid, else None
    """
    capability_idx = get_capability_index()
    valid_types = set(capability_idx.keys())
    # 1. Resource type check
    if resource not in valid_types:
        close = difflib.get_close_matches(resource, valid_types, n=3)
        diagnostics = f"Resource type '{resource}' is not supported. Supported types: {sorted(valid_types)}."
        if close:
            diagnostics += f" Did you mean: {', '.join(close)}?"
        error_data = {
            "resource_type": resource,
            "status_code": 400,
            "diagnostics": diagnostics,
            "issues": [{
                "severity": "error",
                "code": "invalid-type",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("invalid-type", error_data)
        return False, (jsonify(aix_error.model_dump()), 400)
    # 2. Query parameter name check
    supported_param_objs = capability_idx[resource]
    supported_params = {p["name"] for p in supported_param_objs if p["name"]}

    # --- Duplicate/conflicting param check ---
    # Flask's request.args is a MultiDict; query_params may be MultiDict or dict
    param_counts = {}
    for key in query_params:
        # query_params.getlist(key) works for MultiDict, returns all values for key
        values = query_params.getlist(key) if hasattr(query_params, 'getlist') else [query_params[key]]
        if len(values) > 1:
            param_counts[key] = len(values)
    if param_counts:
        param_list = ', '.join(f"'{k}' ({v} times)" for k, v in param_counts.items())
        diagnostics = f"Duplicate/conflicting parameter(s) detected: {param_list}. Each parameter should appear only once per request."
        error_data = {
            "resource_type": resource,
            "status_code": 400,
            "supported_param_schema": supported_param_objs,  # For markdown table
            "supported_params": [p["name"] for p in supported_param_objs if p["name"]],
            "diagnostics": diagnostics,
            "issues": [{
                "severity": "error",
                "code": "duplicate-param",
                "diagnostics": diagnostics
            }],
            # Add any other fields required by error_renderer or CODE_ERROR_DEFS
        }
        aix_error = render_error("invalid_param", error_data)
        return False, (jsonify(aix_error.model_dump()), 400)

    unknown_params = [p for p in query_params if p not in supported_params]
    if unknown_params:
        suggestions = []
        for p in unknown_params:
            close = difflib.get_close_matches(p, supported_params, n=1)
            if close:
                suggestions.append(f"'{p}' → '{close[0]}'")
        diagnostics = f"Unsupported parameter(s) for resource '{resource}': {unknown_params}."
        if suggestions:
            diagnostics += " Did you mean: " + ", ".join(suggestions)
        error_data = {
            "resource_type": resource,
            "status_code": 400,
            "supported_params": ', '.join(sorted(supported_params)),
            "supported_param_schema": supported_param_objs,  # Restore for renderer
            "diagnostics": diagnostics,
            "issues": [{
                "severity": "error",
                "code": "invalid-param",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("invalid_param", error_data)
        return False, (jsonify(aix_error.model_dump()), 400)
    # 3. Empty query check
    if not query_params:
        diagnostics = f"No query parameters provided. Please specify at least one search parameter for resource '{resource}'."
        error_data = {
            "resource_type": resource,
            "status_code": 400,
            "supported_param_schema": supported_param_objs,  # Restore for renderer
            "diagnostics": diagnostics,
            "issues": [{
                "severity": "error",
                "code": "missing-param",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("missing_param", error_data)
        return False, (jsonify(aix_error.model_dump()), 400)
    # TODO: Add value format checks, reserved param warnings, etc.
    return True, None

def _enrich_search_resource_error(resource: str, fhir_response: requests.Response) -> tuple:
    """
    Handle and enrich error messages from FHIR server responses for /searchResource.
    Returns (Flask response, HTTP status code).
    
    TODO: Handle invalid search parameter values (400):
        - Identify which parameter(s) are invalid
        - Provide expected format or allowed values
        - Suggest corrections if possible

    TODO: Handle unsupported/unknown search parameters (400):
        - List unsupported parameter(s)
        - Suggest closest valid parameters
        - Show markdown table of supported parameters

    TODO: Handle malformed requests (400):
        - Show problematic part of request
        - Suggest correct structure

    TODO: Handle OperationOutcome with multiple issues (400/422):
        - Aggregate issues in a readable format
        - Prioritize actionable diagnostics

    TODO: Handle 404 Not Found (if not treating as empty result):
        - Explain no match for search criteria
        - Suggest next steps

    TODO: Handle 405/422 errors:
        - Explain why the request method/entity is not allowed/processable
        - Suggest corrections
"""
    # Implementation will parse the FHIR OperationOutcome and enrich as needed.
    # For now, return a generic error response as a placeholder.
    diagnostics = f"FHIR server returned status {fhir_response.status_code}: {fhir_response.text}"
    error_data = {
        "resource_type": resource,
        "status_code": fhir_response.status_code,
        "issues": [{
            "severity": "error",
            "code": "unknown",
            "diagnostics": diagnostics
        }],
    }
    aix_error = render_error("unknown_error", error_data)
    return jsonify(aix_error.model_dump()), fhir_response.status_code

@app.route('/readResource/<resource>/<resource_id>', methods=['GET'])
def read_resource(resource: str, resource_id: str) -> Response:
    valid_types = set(get_capability_index().keys())
    if resource not in valid_types:
        close = difflib.get_close_matches(resource, valid_types, n=3)
        diagnostics = f"Resource type '{resource}' is not supported. Supported types: {sorted(valid_types)}."
        if close:
            diagnostics += f" Did you mean: {', '.join(close)}?"
        error_data = {
            "resource_type": resource,
            "resource_id": resource_id,
            "status_code": 400,
            "diagnostics": diagnostics,
            "issues": [{
                "severity": "error",
                "code": "invalid-type",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("invalid-type", error_data)
        return jsonify(aix_error.model_dump()), 400

    print(f"resource_id received: '{resource_id}'")
    if not FHIR_ID_PATTERN.match(resource_id):
        diagnostics = f"The ID '{resource_id}' is not valid for resource type '{resource}'. Expected format: [A-Za-z0-9-\\.]{{1,64}}."
        error_data = {
            "resource_type": resource,
            "resource_id": resource_id,
            "status_code": 400,
            "expected_id_format": "[A-Za-z0-9-\\.]{{1,64}}",  # Added for error template
            "issues": [{
                "severity": "error",
                "code": "invalid-id",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("invalid_id", error_data)
        return jsonify(aix_error.model_dump()), 400

    fhir_url = f"{FHIR_SERVER_URL}/{resource}/{resource_id}"
    proxied = requests.get(fhir_url)
    safe_headers = filter_headers(proxied.headers)
    if 200 <= proxied.status_code < 300:
        resp = make_response(proxied.content, proxied.status_code)
        for k, v in safe_headers.items():
            resp.headers[k] = v
        return resp
    else:
        print(f"Proxy error from FHIR server: status={proxied.status_code}, body={proxied.text}")
        try:
            error_body = proxied.json()
            if (
                isinstance(error_body, dict)
                and error_body.get("resourceType") == "OperationOutcome"
                and any(issue.get("code") == "not-found" for issue in error_body.get("issue", []))
            ):
                diagnostics = f"No {resource} resource was found with ID '{resource_id}'."
                error_data = {
                    "resource_type": resource,
                    "resource_id": resource_id,
                    "status_code": proxied.status_code,
                    "issues": [{
                        "severity": "error",
                        "code": "not-found",
                        "diagnostics": diagnostics
                    }],
                }
                aix_error = render_error("not_found", error_data)
                return jsonify(aix_error.model_dump()), proxied.status_code
        except Exception as ex:
            print(f"Error parsing FHIR error response: {ex}")
        # Fallback for plain text or unknown errors
        diagnostics = f"FHIR server returned status {proxied.status_code}: {proxied.text}"
        error_data = {
            "resource_type": resource,
            "resource_id": resource_id,
            "status_code": proxied.status_code,
            "issues": [{
                "severity": "error",
                "code": "unknown",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("unknown_error", error_data)
        return jsonify(aix_error.model_dump()), proxied.status_code

@app.route('/searchResource/<resource>', methods=['GET'])
def search_resource(resource):
    is_valid, error_response = _prevalidate_search_resource(resource, request.args)
    if not is_valid:
        return error_response
    # Forward query params to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}"
    resp = requests.get(fhir_url, params=request.args)
    if resp.status_code >= 400:
        return _enrich_search_resource_error(resource, resp)
    filtered_headers = filter_headers(resp.headers)
    return Response(resp.content, status=resp.status_code, headers=filtered_headers)

@app.route('/openapi.yaml')
def openapi_yaml():
    return send_file(os.path.join(os.path.dirname(__file__), '..', 'openapi.yaml'), mimetype='application/yaml')

@app.errorhandler(404)
def handle_404(e):
    resource_type = request.view_args.get('resource') if request.view_args and 'resource' in request.view_args else None
    resource_id = request.view_args.get('resource_id') if request.view_args and 'resource_id' in request.view_args else None
    diagnostics = getattr(e, 'description', str(e))
    error_data = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status_code": 404,
        "issues": [{
            "severity": "error",
            "code": "not-found",
            "diagnostics": diagnostics
        }],
    }
    aix_error = render_error("not_found", error_data)
    return jsonify(aix_error.model_dump()), 404

@app.errorhandler(400)
def handle_400(e):
    resource_type = request.view_args.get('resource') if request.view_args and 'resource' in request.view_args else None
    resource_id = request.view_args.get('resource_id') if request.view_args and 'resource_id' in request.view_args else None
    diagnostics = getattr(e, 'description', str(e))
    error_data = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status_code": 400,
        "issues": [{
            "severity": "error",
            "code": "invalid",
            "diagnostics": diagnostics
        }],
    }
    aix_error = render_error("unknown_error", error_data)
    return jsonify(aix_error.model_dump()), 400

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PROXY_PORT", 8888))
    app.run(debug=True, port=port)
