from flask import Flask, request, jsonify
import requests
import difflib
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")

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

capability_index = load_capability_statement()

@app.route('/readResource/<resource>/<resource_id>', methods=['GET'])
def read_resource(resource, resource_id):
    # Forward request to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}/{resource_id}"
    resp = requests.get(fhir_url)
    return (resp.content, resp.status_code, resp.headers.items())

@app.route('/searchResource/<resource>', methods=['GET'])
def search_resource(resource):
    # Forward query params to FHIR server
    fhir_url = f"{FHIR_SERVER_URL}/{resource}"
    resp = requests.get(fhir_url, params=request.args)
    # TODO: Add enhanced error feedback, soft error handling, etc.
    return (resp.content, resp.status_code, resp.headers.items())

if __name__ == '__main__':
    app.run(debug=True)
