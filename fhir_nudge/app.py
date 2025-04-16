from flask import Flask, request, jsonify, Response, make_response, abort
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
    { resource_type: set([supported_param1, ...]), ... }
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
                search_params = {param["name"] for param in resource.get("searchParam", []) if "name" in param}
                index[resource_type] = search_params
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
            "issues": [{
                "severity": "error",
                "code": "invalid-type",
                "diagnostics": diagnostics
            }],
        }
        aix_error = render_error("invalid_resource_type", error_data)
        return jsonify(aix_error.model_dump()), 400

    if not FHIR_ID_PATTERN.match(resource_id):
        diagnostics = f"The ID '{resource_id}' is not valid for resource type '{resource}'. Expected format: [A-Za-z0-9-\\.]{{1,64}}."
        error_data = {
            "resource_type": resource,
            "resource_id": resource_id,
            "status_code": 400,
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
    # Forward query params to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}"
    resp = requests.get(fhir_url, params=request.args)
    # TODO: Add enhanced error feedback, soft error handling, etc.
    return (resp.content, resp.status_code, dict(resp.headers))

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
    app.run(debug=True)
