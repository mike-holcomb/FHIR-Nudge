"""HTTP client for interacting with a FHIR Nudge proxy server.

Provides simple read and search methods via HTTP to the proxy.
Raises `requests.exceptions.HTTPError` for non-2xx responses and
`requests.exceptions.Timeout` if a request times out.

Usage:
    client = FhirNudgeClient("http://localhost:8888")
    client.read_resource("Patient", "123")
    client.search_resource("Observation", {"code": "1234-5"})
"""
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

class FhirNudgeClient:
    """
    HTTP client for interacting with a FHIR Nudge proxy server.

    Provides methods to read and search FHIR resources through the proxy.

    Raises:
        requests.exceptions.HTTPError: for any non-2xx HTTP response
        requests.exceptions.Timeout: if a request exceeds the timeout

    Examples:
        >>> client = FhirNudgeClient("http://localhost:8888", timeout=5)
        >>> client.read_resource("Patient", "123")
        {'resourceType': 'Patient', ...}
        >>> client.search_resource("Observation", {"code": "1234-5"})
        {'resourceType': 'Bundle', ...}
    """
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialize the client.

        Args:
            base_url: The base URL of the FHIR Nudge proxy (e.g., 'http://localhost:8888'). A trailing slash will be stripped.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def read_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """
        Fetch a FHIR resource by type and ID.

        Args:
            resource_type: The FHIR resource type (e.g., 'Patient').
            resource_id: The resource ID.

        Returns:
            The resource as a dict.

        Raises:
            requests.exceptions.HTTPError: on non-2xx HTTP response.
            requests.exceptions.Timeout: if the request times out.
        """
        path = f"/readResource/{resource_type}/{resource_id}"
        url = urljoin(self.base_url + '/', path)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search_resource(self, resource_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for FHIR resources of a given type with specified query parameters.

        Args:
            resource_type: The FHIR resource type (e.g., 'Patient').
            params: Dictionary of search parameters (e.g., {'name': 'Smith', 'gender': 'female'}).

        Returns:
            The search result as a dict (usually a FHIR Bundle).

        Raises:
            requests.exceptions.HTTPError: on non-2xx HTTP response.
            requests.exceptions.Timeout: if the request times out.
        """
        path = f"/searchResource/{resource_type}"
        url = urljoin(self.base_url + '/', path)
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # TODO: Implement create_resource(self, resource_type: str, resource: dict) -> dict
    # Should POST the resource dict to /createResource/{resource_type} and return the created resource.
    # TODO: Implement update_resource(self, resource_type: str, resource_id: str, resource: dict) -> dict
    # Should PUT the resource dict to /updateResource/{resource_type}/{resource_id} and return the updated resource.
    # TODO: Implement delete_resource(self, resource_type: str, resource_id: str) -> dict
    # Should DELETE /deleteResource/{resource_type}/{resource_id} and return deletion outcome.
    # TODO: Implement get_capability_statement(self) -> dict
    # Should GET /metadata to retrieve the FHIR server's CapabilityStatement.
