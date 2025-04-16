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
import subprocess
import time
import signal
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fhir_nudge.client import FhirNudgeClient

# Config: Change as needed for your environment
PROXY_URL = "http://localhost:8888"  # The running Flask proxy
TEST_PATIENT_ID = "S6426560"  # Replace with a real Patient ID on your FHIR server

def start_proxy():
    # Start the Flask proxy as a subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    proc = subprocess.Popen(
        [sys.executable, "-m", "fhir_nudge.app"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for the server to come up or fail
    for _ in range(20):  # wait up to ~10s
        try:
            resp = requests.get("http://localhost:8888/health", timeout=0.5)
            if resp.status_code in (200, 404):
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            break  # Process exited
        time.sleep(0.5)
    # Check if process died or port is still occupied
    out, err = proc.communicate(timeout=2)
    if b"Address already in use" in err or b"Address already in use" in out:
        print("\nERROR: Could not start proxy server: port 8888 is already in use.\n", file=sys.stderr)
        sys.exit(2)
    print("\nERROR: Proxy server did not start successfully.\n", file=sys.stderr)
    print(out.decode())
    print(err.decode())
    sys.exit(2)

def stop_proxy(proc):
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    try:
        out, err = proc.communicate(timeout=2)
        print(out.decode())
        print(err.decode())
    except Exception:
        pass

def test_read_patient():
    print("Test: Read Patient by ID...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        patient = client.read_resource("Patient", TEST_PATIENT_ID)
        assert patient["resourceType"] == "Patient"
        assert patient["id"] == TEST_PATIENT_ID
        print("  PASS")
    except requests.HTTPError as e:
        print(f"  FAIL: HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Raw response: {e.response.text}")
        global failures
        failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_nonexistent_patient():
    print("Test: Read non-existent Patient...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.read_resource("Patient", "doesnotexist12345")
        print("  FAIL: Expected HTTP 404, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print(f"  PASS (caught expected 404): {e}")
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_invalid_resource():
    print("Test: Read invalid resource type...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.read_resource("NotAType", "123")
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        print(f"  HTTPError: {e}")
        if e.response is not None:
            print(f"  Raw response: {e.response.text}")
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                print(f"  Parsed JSON: {err}")
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                print(f"  Extracted diagnostics: {diags}")
                assert "is not supported" in diags
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_invalid_id_format():
    print("Test: Read Patient with invalid ID format...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.read_resource("Patient", "invalid id!")
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                assert "not valid for resource type" in diags or "invalid" in diags
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_read_fuzzy_resource_type():
    print("Test: Read with fuzzy resource type (typo)...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.read_resource("Patiant", "123")
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                assert "Did you mean:" in diags
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

if __name__ == "__main__":
    proxy_proc = start_proxy()
    try:
        failures = 0
        test_read_patient()
        test_read_nonexistent_patient()
        test_read_invalid_resource()
        test_read_invalid_id_format()
        test_read_fuzzy_resource_type()
        if failures:
            print(f"\n{failures} test(s) failed.")
            sys.exit(1)
        print("\nAll E2E tests passed!")
        sys.exit(0)
    finally:
        stop_proxy(proxy_proc)
