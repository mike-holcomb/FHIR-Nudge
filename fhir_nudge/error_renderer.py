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
    # Add more error types here as needed
}

def render_error(error_type: str, error_data: dict) -> AIXErrorResponse:
    """
    Render an AIXErrorResponse using code-based templates, with best-effort context.

    Args:
        error_type: str, e.g. 'not_found', 'invalid_id', 'unknown_error'
        error_data: dict with keys as required by error_type

    Returns:
        AIXErrorResponse instance
    """
    error_def = CODE_ERROR_DEFS.get(error_type)
    missing = []
    if error_def:
        required = error_def.get("required_fields", [])
        for f in required:
            if error_data.get(f) is None:
                missing.append(f)
        # Use available fields for formatting, fallback to placeholders for missing
        format_data = {k: (v if v is not None else f"<missing {k}>") for k, v in error_data.items()}
        for f in required:
            if f not in format_data:
                format_data[f] = f"<missing {f}>"
        friendly_message = error_def["template"].format(**format_data)
        next_steps = error_def.get("next_steps", "").format(**format_data)
        error_text = error_type.replace('_', ' ').capitalize()
        issues = error_data.get("issues", [])
        if missing:
            extra_diag = f"Warning: Missing fields for this error: {missing}"
            issues = list(issues) + [{
                "severity": "information",
                "code": "incomplete-context",
                "diagnostics": extra_diag,
                "details": "<missing details>"  # TODO: Patch with real details if available
            }]
    else:
        friendly_message = "An error occurred."
        next_steps = None
        error_text = error_type.replace('_', ' ').capitalize()
        issues = error_data.get("issues", [])

    # Patch all issues to include required fields for OperationOutcomeIssue
    patched_issues = []
    for issue in issues:
        patched_issues.append({
            "severity": issue.get("severity", "error"),
            "code": issue.get("code", "unknown"),
            "diagnostics": issue.get("diagnostics", "<missing diagnostics>"),
            "details": issue.get("details", "<missing details>")  # TODO: Patch with real details if available
        })

    return AIXErrorResponse(
        error=error_text,
        friendly_message=friendly_message,
        next_steps=next_steps,
        resource_type=error_data.get("resource_type"),
        resource_id=error_data.get("resource_id"),
        status_code=error_data.get("status_code") if error_data.get("status_code") is not None else -1,  # TODO: Patch with real status if available
        issues=patched_issues,
    )
