from .schemas import AIXErrorResponse

# Unified code-based error definitions
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

def render_param_schema_markdown(supported_param_schema):
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

def render_error(error_type: str, error_data: dict) -> AIXErrorResponse:
    """
    Render an AIXErrorResponse using code-based templates, with best-effort context.

    Args:
        error_type: str, e.g. 'not_found', 'invalid_id', 'unknown_error'
        error_data: dict with keys as required by error_type

    Returns:
        AIXErrorResponse instance
    """
    supported_param_schema = error_data.get("supported_param_schema")
    pretty_schema = None
    if supported_param_schema:
        pretty_schema = render_param_schema_markdown(supported_param_schema)

    error_def = CODE_ERROR_DEFS.get(error_type)
    missing = []
    # Compose next_steps from template, then prepend markdown table if present
    if error_def:
        friendly_message = error_def["template"].format(**error_data)
        next_steps = error_def.get("next_steps", "").format(**error_data)
        if pretty_schema:
            # Prepend markdown table and an extra newline for readability
            next_steps = f"{pretty_schema}\n\n{next_steps}"
    else:
        friendly_message = error_data.get("diagnostics", "An error occurred.")
        next_steps = error_data.get("next_steps", "")
        if pretty_schema:
            next_steps = f"{pretty_schema}\n\n{next_steps}"

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

    # Patch all issues to include required fields for OperationOutcomeIssue
    patched_issues = []
    for issue in issues:
        patched_issues.append({
            "severity": issue.get("severity", "error"),
            "code": issue.get("code", "unknown"),
            "diagnostics": issue.get("diagnostics", "<missing diagnostics>"),
            "details": issue.get("details", "<missing details>")
        })

    # Add a warning issue only if there are missing required fields
    if missing:
        patched_issues.append({
            "severity": "information",
            "code": "incomplete-context",
            "diagnostics": f"Warning: Missing fields for this error: {missing}",
            "details": "<missing details>"
        })

    # Always include supported_param_schema at top level if present
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
