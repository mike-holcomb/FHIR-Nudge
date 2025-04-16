import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

class FhirNudgeClient:
    """
    Basic client for interacting with a FHIR Nudge proxy server.
    """
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Args:
            base_url: The base URL of the FHIR Nudge proxy (e.g., 'http://localhost:8888').
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
            The resource as a dict, or raises HTTPError on failure.
        """
        path = f"/readResource/{resource_type}/{resource_id}"
        url = urljoin(self.base_url + '/', path)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search_resource(self, resource_type: str, params: dict) -> Dict[str, Any]:
        """
        Search for FHIR resources of a given type with specified query parameters.
        Args:
            resource_type: The FHIR resource type (e.g., 'Patient').
            params: Dictionary of search parameters (e.g., {'name': 'Smith', 'gender': 'female'}).
        Returns:
            The search result as a dict (usually a FHIR Bundle), or raises HTTPError on failure.
        """
        path = f"/searchResource/{resource_type}"
        url = urljoin(self.base_url + '/', path)
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # TODO: Implement create_resource(self, resource_type: str, resource: dict) -> dict
    # TODO: Implement update_resource(self, resource_type: str, resource_id: str, resource: dict) -> dict
    # TODO: Implement delete_resource(self, resource_type: str, resource_id: str) -> dict
    # TODO: Implement get_capability_statement(self) -> dict
