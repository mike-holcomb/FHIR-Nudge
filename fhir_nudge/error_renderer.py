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
    Render an AIXErrorResponse using code-based templates.

    Args:
        error_type: str, e.g. 'not_found', 'invalid_id', 'unknown_error'
        error_data: dict with keys as required by error_type

    Returns:
        AIXErrorResponse instance

    Raises:
        ValueError if required fields are missing for the given error_type.
    """
    error_def = CODE_ERROR_DEFS.get(error_type)
    if error_def:
        required = error_def.get("required_fields", [])
        missing = [field for field in required if field not in error_data]
        if missing:
            raise ValueError(f"Missing required fields for '{error_type}': {missing}")

        friendly_message = error_def["template"].format(**error_data)
        next_steps_template = error_def.get("next_steps")
        next_steps = next_steps_template.format(**error_data) if next_steps_template else None
        error_text = error_type.replace('_', ' ').capitalize()
    else:
        # Generic fallback for unknown errors
        friendly_message = "An error occurred."
        next_steps = None
        error_text = error_type.replace('_', ' ').capitalize()

    return AIXErrorResponse(
        error=error_text,
        friendly_message=friendly_message,
        next_steps=next_steps,
        resource_type=error_data.get("resource_type"),
        resource_id=error_data.get("resource_id"),
        status_code=error_data.get("status_code"),
        issues=error_data.get("issues", []),
    )
