# Error Handling Guidelines for FHIR Nudge

This document provides detailed guidance for developers and contributors on how to implement, extend, and maintain error handling in the FHIR Nudge codebase, with a focus on the hybrid approach that combines code-based and registry/template-based error messages.

---

## Overview

FHIR Nudge aims to deliver actionable, user-friendly, and AI/LLM-optimized error messages. To achieve this, we use a **hybrid error handling system**:
- **Code-based errors** for simple, generic, or internal errors.
- **Registry/template-based errors** for user-facing, customizable, or localized messages.
- **Hybrid:** Registry is checked first; code-based is the fallback.

---

## Code-Based Error Handling: Unified Dictionary Approach

As of the current implementation, **all code-based error templates, next steps, and required fields are managed in a single dictionary called `CODE_ERROR_DEFS` in `fhir_nudge/error_renderer.py`**. This eliminates the need to update multiple mappings and makes it much easier to add or update code-based errors.

### Example Structure

```python
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
```

### How to Add a New Code-Based Error
- Add a new entry to `CODE_ERROR_DEFS` with:
  - `template`: The main error message, using Python string formatting with placeholders.
  - `next_steps`: (Optional) Actionable guidance, also supporting placeholders.
  - `required_fields`: List of fields that must be present in `error_data`.
- The error rendering logic will automatically check for required fields and raise a clear error if any are missing.

---

## When to Use Each Error Type

### Code-Based Errors
- **Use when:**
  - The error is simple, static, and unlikely to change (e.g., "resource not found", "invalid ID format").
  - The message is not user-facing or does not require localization/customization.
  - You want minimal dependencies and maximum performance.
- **How:**
  - Add an entry to `CODE_ERROR_DEFS` in Python.

### Registry/Template-Based Errors
- **Use when:**
  - The error is user-facing and may need updates by non-developers (PMs, writers, translators).
  - The message is complex, varies by resource, or is subject to localization.
  - You want to iterate on messaging or support multiple languages without code changes.
  - The error involves dynamic data (e.g., listing supported search params, validation feedback).
- **How:**
  - Add a template JSON file in `error_registry/` (e.g., `not_found.json`, `searchparam_error.json`).
  - Use placeholders for dynamic fields (e.g., `{resource_type}`, `{param}`).

### Hybrid (Both)
- **Use when:**
  - You want the flexibility to override generic messages for specific resources or error types.
  - Use code-based as a fallback for generic cases, and registry-based for user-facing or evolving messages.
- **How:**
  - The error renderer first tries to load a registry/template-based message.
  - If not found, it uses the code-based default.
  - Only add a new registry template if the message needs to be user-facing, localized, or customized.

---

## Examples

| Scenario                           | Use Code | Use Registry | Notes                                   |
|-------------------------------------|:--------:|:------------:|-----------------------------------------|
| Resource not found                  |    ✓     |      ✓*      | Use code for generic, registry for custom|
| Search param not supported          |          |      ✓       | Registry allows for dynamic suggestions  |
| Validation failed (POST/PUT)        |          |      ✓       | Registry for user guidance, code for debug|
| Server unavailable                  |    ✓     |              | Simple, internal error                   |
| Localization required               |          |      ✓       | Registry supports multiple languages     |

*Use registry only if you want a custom message for a particular resource.

---

## Fallback Logic

1. The error rendering engine will first look for a registry/template override (resource-specific or generic).
2. If not found, it will use the code-based default from `CODE_ERROR_DEFS`.
3. Developers should only add a new registry template if the message needs to be user-facing, localized, or customized.

---

## Onboarding Checklist for Contributors

1. **When adding a new code-based error:**
    - Add a new entry to `CODE_ERROR_DEFS` in `fhir_nudge/error_renderer.py`.
    - Specify the `template`, `next_steps`, and `required_fields`.
    - Document any new placeholders used in your templates.
2. **When adding a new registry/template-based error:**
    - Add a new template file to `error_registry/` with placeholders and documentation.
3. **Add/modify tests** to cover the new error path.

---

## Code Comments and Documentation

- In `error_renderer.py`, add docstrings/comments explaining the unified dictionary approach and the lookup order.
- Example:
  ```python
  """
  Error rendering order:
    1. Try to load a registry/template-based message for the error type.
    2. If not found, use the code-based message from CODE_ERROR_DEFS.
  Use registry for user-facing, customizable, or localized errors.
  Use code for simple, generic, or internal errors.
  All code-based errors are defined in CODE_ERROR_DEFS as a single source of truth.
  """
  ```

---

## Summary Table

| Error Type         | Code-Based | Registry-Based | Both (Hybrid) |
|--------------------|:----------:|:--------------:|:-------------:|
| Simple, internal   |     ✓      |                |               |
| User-facing, static|     ✓      |      ✓         |      ✓        |
| User-facing, dynamic|           |      ✓         |      ✓        |
| Needs localization |            |      ✓         |      ✓        |
| Debug-only         |     ✓      |                |               |

---

For further details, see the implementation in `error_renderer.py` and the templates in `error_registry/`.
