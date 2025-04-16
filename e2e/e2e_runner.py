"""
End-to-end tests for FHIR Nudge proxy using the real client and a live FHIR server.

Usage:
  1. Ensure the Flask proxy is running and FHIR_SERVER_URL is set to a live FHIR server.
  2. Run this script: python e2e/e2e_runner.py
  3. The script will exit 0 if all tests pass, nonzero otherwise.
"""
import sys
import os
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fhir_nudge.client import FhirNudgeClient

# Config: Change as needed for your environment
PROXY_URL = "http://localhost:8888"  # The running Flask proxy
TEST_PATIENT_ID = "example"  # Replace with a real Patient ID on your FHIR server

client = FhirNudgeClient(PROXY_URL)

failures = 0

def test_read_patient():
    print("Test: Read Patient by ID...")
    try:
        patient = client.read_resource("Patient", TEST_PATIENT_ID)
        assert patient["resourceType"] == "Patient"
        assert patient["id"] == TEST_PATIENT_ID
        print("  PASS")
    except requests.HTTPError as e:
        print(f"  FAIL: HTTP error: {e}")
        global failures
        failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_nonexistent_patient():
    print("Test: Read non-existent Patient...")
    try:
        client.read_resource("Patient", "doesnotexist12345")
        print("  FAIL: Expected HTTP 404, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print(f"  PASS (caught expected 404): {e}")
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_invalid_resource():
    print("Test: Read invalid resource type...")
    try:
        client.read_resource("NotAType", "123")
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            print(f"  PASS (caught expected 400): {e}")
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

if __name__ == "__main__":
    test_read_patient()
    test_read_nonexistent_patient()
    test_read_invalid_resource()
    if failures:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
    print("\nAll E2E tests passed!")
    sys.exit(0)
