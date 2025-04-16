from flask import Flask, request, jsonify, Response, make_response
import requests
import difflib
from dotenv import load_dotenv
import os
import re

# TODO: Refactor capability_index (knowledgebase) into its own class for better testability and maintainability.

app = Flask(__name__)

load_dotenv()
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")
FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-\.]{1,64}$")

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
    excluded = {
        'Transfer-Encoding', 'Content-Encoding', 'Content-Length', 'Connection',
        'Keep-Alive', 'Proxy-Authenticate', 'Proxy-Authorization', 'TE', 'Trailer', 'Upgrade'
    }
    return {k: v for k, v in headers.items() if k not in excluded}

capability_index = None

def get_capability_index():
    global capability_index
    if capability_index is None:
        capability_index = load_capability_statement()
    return capability_index

@app.route('/readResource/<resource>/<resource_id>', methods=['GET'])
def read_resource(resource: str, resource_id: str) -> Response:
    # Step 1: Prevalidate resource type
    valid_types = set(get_capability_index().keys())
    if resource not in valid_types:
        close = difflib.get_close_matches(resource, valid_types, n=3)
        msg = {
            "error": f"Resource type '{resource}' is not supported by the FHIR server.",
            "supported_types": sorted(valid_types),
        }
        if close:
            msg["did_you_mean"] = close
        return make_response(jsonify(msg), 400)

    # Step 2: Validate resource_id format
    if not FHIR_ID_PATTERN.match(resource_id):
        return make_response(jsonify({
            "error": "Invalid resource_id format. Must match FHIR id pattern [A-Za-z0-9-\\.]{1,64}."
        }), 400)

    # Step 3: Forward request to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}/{resource_id}"
    proxied = requests.get(fhir_url)
    safe_headers = filter_headers(proxied.headers)
    resp = make_response(proxied.content, proxied.status_code)
    for k, v in safe_headers.items():
        resp.headers[k] = v
    return resp

@app.route('/searchResource/<resource>', methods=['GET'])
def search_resource(resource):
    # Forward query params to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}"
    resp = requests.get(fhir_url, params=request.args)
    # TODO: Add enhanced error feedback, soft error handling, etc.
    return (resp.content, resp.status_code, dict(resp.headers))

if __name__ == '__main__':
    app.run(debug=True)
