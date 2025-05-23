"""Unified error rendering for FHIR Nudge proxy.
Provides functions to render `AIXErrorResponse` using code-based templates and optional parameter-schema markdown.
See docs/AIX_ERROR_SCHEMA.md and docs/ERROR_HANDLING_GUIDELINES.md for details.
"""
from .schemas import AIXErrorResponse
from typing import List, Dict, Any, Optional
import logging

## CODE_ERROR_DEFS: unified mapping of error types to template definitions
# Keys:
#   - template: Python format string for friendly_message
#   - next_steps: guidance string, may include markdown
#   - required_fields: list of context keys that must be present
CODE_ERROR_DEFS = {
    "not_found": {
        "template": "No {resource_type} resource was found with ID '{resource_id}'.",
        "next_steps": "Try searching for the {resource_type} using /searchResource.",
        "required_fields": ["resource_type", "resource_id", "status_code"],
    },
    "invalid_id": {
        "template": "The ID '{resource_id}' is not valid for resource type '{resource_type}'.",
        "next_steps": "Check the format of '{resource_id}' and try again. Expected format: {expected_id_format}. Consult the documentation if unsure.",
        "required_fields": ["resource_type", "resource_id", "status_code", "expected_id_format"],
    },
    "invalid_param": {
        "template": "Parameter(s) provided are not supported for resource '{resource_type}'. {diagnostics}",
        "next_steps": "Supported search parameters for '{resource_type}': {supported_params}. Correct any typos or use one of these parameters.",
        "required_fields": ["resource_type", "status_code", "supported_params"],
    },
    "missing_param": {
        "template": "No query parameters were provided for resource '{resource_type}'. At least one search parameter is required.",
        "next_steps": "Specify at least one valid search parameter for '{resource_type}'. See the API documentation for supported parameters.",
        "required_fields": ["resource_type", "status_code"],
    },
    "invalid-type": {
        "template": "Resource type '{resource_type}' is not supported.",
        "next_steps": "Check the spelling or refer to the list of supported resource types.",
        "required_fields": ["resource_type", "status_code"],
    },
    # Add more error types here as needed
}

def render_param_schema_markdown(supported_param_schema: List[Dict[str, Any]]) -> str:
    """
    Generate a markdown table for supported search parameters.

    Args:
        supported_param_schema: list of dicts with 'name', 'type', 'documentation', 'example'.

    Returns:
        Markdown-formatted table string for embedding in error messages.
    """
    # Pretty print as a markdown table
    headers = ["name", "type", "documentation", "example"]
    rows = []
    for param in supported_param_schema:
        row = [param.get(h, "") or "" for h in headers]
        rows.append(row)
    # Build markdown table
    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
    for row in rows:
        table.append("| " + " | ".join(row) + " |")
    return "\n".join(table)

def render_error(error_type: str, error_data: Dict[str, Any]) -> AIXErrorResponse:
    """
    Build and return an AIXErrorResponse by applying the selected template and context.

    Workflow:
    1. Optionally format 'supported_param_schema' as markdown table.
    2. Lookup the error definition in CODE_ERROR_DEFS; fallback if missing.
    3. Format 'friendly_message' and 'next_steps', prepending parameter table if provided.
    4. Validate 'required_fields' and collect missing keys for warning.
    5. Normalize each issue dict to include all schema fields ('severity','code','diagnostics','details').
    6. Append an 'incomplete-context' issue if any required fields are missing.
    7. Instantiate and return the AIXErrorResponse model.

    Args:
        error_type: Identifier for template selection (e.g., 'not_found').
        error_data: Context dict supplying template placeholders and raw 'issues'.

    Returns:
        AIXErrorResponse: Fully populated error response.
    """
    supported_param_schema = error_data.get("supported_param_schema")
    pretty_schema = None
    if supported_param_schema:
        pretty_schema = render_param_schema_markdown(supported_param_schema)

    error_def = CODE_ERROR_DEFS.get(error_type)
    missing = []  # Collect any required fields that are not present

    # Render messages from templates if definition exists, otherwise fallback
    if error_def:
        # Prepare safe format_data, filling placeholders for missing required fields
        format_data = dict(error_data)
        for field in error_def.get("required_fields", []):
            if format_data.get(field) is None:
                format_data[field] = "" if field == "diagnostics" else f"<missing {field}>"
        # Render friendly_message
        friendly_message = error_def["template"].format(**format_data)
        # Render next_steps, default to None on failure
        try:
            next_steps = error_def.get("next_steps", "").format(**format_data)
        except Exception:
            next_steps = None
        if pretty_schema:
            # Prepend markdown table for supported params
            next_steps = f"{pretty_schema}\n\n{next_steps}" if next_steps else pretty_schema
    else:
        # Unknown error_type: log warning and use diagnostics fallback
        logging.warning(f"render_error: Unknown error_type '{error_type}'")
        friendly_message = error_data.get("diagnostics", "An error occurred.")
        next_steps = None
        if pretty_schema:
            next_steps = pretty_schema

    error_text = error_type.replace('_', ' ').capitalize()
    issues = error_data.get("issues", [])

    if error_def:
        required = error_def.get("required_fields", [])
        for f in required:
            if error_data.get(f) is None:
                missing.append(f)
        # Use available fields for formatting, fallback to placeholders for missing
        format_data = {k: (v if v is not None else f"<missing {k}>") for k, v in error_data.items()}
        for f in required:
            if f not in format_data:
                # Patch missing diagnostics with empty string for template safety
                format_data[f] = "" if f == "diagnostics" else f"<missing {f}>"

    # Ensure each issue dict conforms to OperationOutcomeIssue schema
    patched_issues = []
    for issue in issues:
        patched_issues.append({
            "severity": issue.get("severity", "error"),
            "code": issue.get("code", "unknown"),
            "diagnostics": issue.get("diagnostics", "<missing diagnostics>"),
            "details": issue.get("details", "<missing details>")
        })

    if missing:
        # Append warning about incomplete context
        patched_issues.append({
            "severity": "information",
            "code": "incomplete-context",
            "diagnostics": f"Warning: Missing fields for this error: {missing}",
            "details": "<missing details>"
        })

    # Construct the AIXErrorResponse model instance
    response = AIXErrorResponse(
        error=error_text,
        friendly_message=friendly_message,
        next_steps=next_steps,
        resource_type=error_data.get("resource_type"),
        resource_id=error_data.get("resource_id"),
        status_code=error_data.get("status_code") if error_data.get("status_code") is not None else -1,
        issues=patched_issues,
    )
    # Do NOT monkeypatch model_dump; let caller add extra fields after model_dump()
    return response
