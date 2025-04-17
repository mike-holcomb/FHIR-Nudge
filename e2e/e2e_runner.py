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
        stdout=None,  # Inherit parent's stdout
        stderr=None,  # Inherit parent's stderr
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
    if proc.poll() is not None:
        out, err = proc.communicate()
        if b"Address already in use" in err or b"Address already in use" in out:
            print("\nERROR: Could not start proxy server: port 8888 is already in use.\n", file=sys.stderr)
            sys.exit(2)
        print("\nERROR: Proxy server did not start successfully.\n", file=sys.stderr)
        print(out.decode())
        print(err.decode())
        sys.exit(2)
    print("\nERROR: Proxy server did not start successfully.\n", file=sys.stderr)
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
        print("\033[91m**FAIL**\033[0m")
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
        print("\033[91m**FAIL**\033[0m")
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
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
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
        print("\033[91m**FAIL**\033[0m")
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
        print("\033[91m**FAIL**\033[0m")
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
                print(f"  FAIL: Could not parse diagnostics or markdown: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_valid():
    """
    Test: Search for Patient with a valid parameter (should return Bundle).
    Requires at least one Patient with name 'John' in the backend FHIR server.
    """
    print("Test: Search Patient (valid param)...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        bundle = client.search_resource("Patient", {"name": "John"})
        assert bundle["resourceType"] == "Bundle"
        assert "entry" in bundle
        print(f"  PASS (entries: {len(bundle['entry']) if 'entry' in bundle else 0})")
    except requests.HTTPError as e:
        print(f"  FAIL: HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Raw response: {e.response.text}")
        global failures
        failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_invalid_param():
    """
    Test: Search with an invalid parameter (should return 400 with actionable diagnostics and markdown guidance).
    """
    print("Test: Search Patient with invalid param...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.search_resource("Patient", {"foobarbaz": "abc"})
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                # Check diagnostics for invalid param
                assert "foobarbaz" in diags
                # Check for markdown table in next_steps
                assert "| name | type | documentation" in err.get("next_steps", "")
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics or markdown: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_missing_param():
    """
    Test: Search with no parameters (should return 400 and actionable diagnostics).
    """
    print("Test: Search Patient with no params...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.search_resource("Patient", {})
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                # Check diagnostics for missing param
                assert "parameter" in diags.lower() or "missing" in diags.lower()
                # Check for markdown table in next_steps
                assert "| name | type | documentation" in err.get("next_steps", "")
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics or markdown: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_invalid_value_format():
    """
    Test: Search with a parameter that has an invalid value format (should return 400 and format diagnostics).
    """
    print("Test: Search Patient with invalid value format...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        # Use a date parameter with an invalid format
        client.search_resource("Patient", {"birthdate": "notadate"})
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                # Check diagnostics for invalid value
                assert (
                    "invalid" in diags.lower()
                    and ("format" in diags.lower() or "date/time" in diags.lower() or "quantity format" in diags.lower())
                )
                # Check for markdown table in next_steps
                assert "| name | type | documentation" in err.get("next_steps", "")
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics or markdown: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_duplicate_param():
    """
    Test: Search with a duplicate/conflicting parameter (should return 400 and duplicate diagnostics).
    Note: requests will collapse duplicate keys unless you use a list of tuples.
    """
    print("Test: Search Patient with duplicate param...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        # Use a list of tuples to send duplicate params
        resp = requests.get(f"{PROXY_URL}/searchResource/Patient", params=[("name", "John"), ("name", "Jane")])
        if resp.status_code == 400:
            err = resp.json()
            diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
            assert "duplicate" in diags.lower() or "conflict" in diags.lower() or "multiple" in diags.lower()
            assert "| name | type | documentation" in err.get("next_steps", "")
            print(f"  PASS (caught expected 400, diagnostics: {diags})")
        else:
            print(f"  FAIL: Expected HTTP 400, got {resp.status_code}")
            print(f"  Raw response: {resp.text}")
            global failures
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_reserved_param():
    """
    Test: Search with a reserved/unknown parameter (should return 400 and reserved param diagnostics).
    """
    print("Test: Search Patient with reserved/unknown param...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        client.search_resource("Patient", {"_internal": "foo"})
        print("  FAIL: Expected HTTP 400, got success")
        global failures
        failures += 1
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            try:
                err = e.response.json()
                diags = " ".join(iss.get("diagnostics", "") for iss in err.get("issues", []))
                assert (
                    "reserved" in diags.lower()
                    or "unknown" in diags.lower()
                    or "not supported" in diags.lower()
                    or "unsupported" in diags.lower()
                )
                assert "| name | type | documentation" in err.get("next_steps", "")
                print(f"  PASS (caught expected 400, diagnostics: {diags})")
            except Exception as ex:
                print(f"  FAIL: Could not parse diagnostics or markdown: {ex}")
                print(f"  Raw response: {e.response.text}")
                failures += 1
        else:
            print(f"  FAIL: Unexpected HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Raw response: {e.response.text}")
            failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_empty_result():
    """
    Test: Search for a Patient with a value that should return no results (should return 200 and empty Bundle).
    """
    print("Test: Search Patient (empty result)...")
    try:
        client = FhirNudgeClient(PROXY_URL)
        bundle = client.search_resource("Patient", {"name": "NoSuchNameXYZ123"})
        assert bundle["resourceType"] == "Bundle"
        assert "entry" not in bundle or len(bundle["entry"]) == 0
        print("  PASS (empty result)")
    except requests.HTTPError as e:
        print(f"  FAIL: HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Raw response: {e.response.text}")
        global failures
        failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def test_search_resource_upstream_error():
    """
    Test: Simulate backend FHIR server failure (should return 502 and upstream error diagnostics).
    TODO: Requires backend FHIR server to be offline or misconfigured for this test.
    """
    print("Test: Search Patient (upstream error)...")
    try:
        # Temporarily misconfigure backend or stop FHIR server for this test
        # This is a placeholder; implementation will depend on your test infra
        print("  SKIP: Not implemented (requires backend FHIR server offline)")
        # client = FhirNudgeClient(PROXY_URL)
        # client.search_resource("Patient", {"name": "John"})
        # print("  FAIL: Expected HTTP 502, got success")
        # global failures
        # failures += 1
    except Exception as e:
        print("\033[91m**FAIL**\033[0m")
        print(f"  FAIL: Unexpected error: {e}")
        failures += 1

def print_separator():
    print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    proxy_proc = start_proxy()
    try:
        failures = 0
        test_read_patient()
        print_separator()
        test_read_nonexistent_patient()
        print_separator()
        test_read_invalid_resource()
        print_separator()
        test_read_invalid_id_format()
        print_separator()
        test_read_fuzzy_resource_type()
        print_separator()
        test_search_resource_valid()
        print_separator()
        test_search_resource_invalid_param()
        print_separator()
        test_search_resource_missing_param()
        print_separator()
        test_search_resource_invalid_value_format()
        print_separator()
        test_search_resource_duplicate_param()
        print_separator()
        test_search_resource_reserved_param()
        print_separator()
        test_search_resource_empty_result()
        print_separator()
        test_search_resource_upstream_error()
        print_separator()
        if failures:
            print(f"\n{failures} test(s) failed.")
            sys.exit(1)
        print("\nAll E2E tests passed!")
        sys.exit(0)
    finally:
        stop_proxy(proxy_proc)
