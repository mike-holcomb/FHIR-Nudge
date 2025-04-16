# Error Handling Guidelines for FHIR Nudge

This document provides detailed guidance for developers and contributors on how to implement, extend, and maintain error handling in the FHIR Nudge codebase, with a focus on the hybrid approach that combines code-based and registry/template-based error messages.

---

## Overview

FHIR Nudge aims to deliver actionable, user-friendly, and AI/LLM-optimized error messages. To achieve this, we use a **hybrid error handling system**:
- **Code-based errors** for simple, generic, or internal errors.
- **Registry/template-based errors** for user-facing, customizable, or localized messages.
- **Hybrid:** Registry is checked first; code-based is the fallback.

---

## When to Use Each Error Type

### Code-Based Errors
- **Use when:**
  - The error is simple, static, and unlikely to change (e.g., "resource not found", "invalid ID format").
  - The message is not user-facing or does not require localization/customization.
  - You want minimal dependencies and maximum performance.
- **How:**
  - Implement as string templates or helper functions in Python.
  - Example: `code_based_not_found()` in `error_renderer.py`.

### Registry/Template-Based Errors
- **Use when:**
  - The error is user-facing and may need updates by non-developers (PMs, writers, translators).
  - The message is complex, varies by resource, or is subject to localization.
  - You want to iterate on messaging or support multiple languages without code changes.
  - The error involves dynamic data (e.g., listing supported search params, validation feedback).
- **How:**
  - Add a template JSON file in `error_registry/` (e.g., `not_found.json`, `searchparam_error.json`).
  - Use placeholders for dynamic fields (e.g., `{resource_type}`, `{param}`).
  - Example: See `error_registry/not_found.json`.

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
2. If not found, it will use the code-based default.
3. Developers should only add a new registry template if the message needs to be user-facing, localized, or customized.

---

## Onboarding Checklist for Contributors

1. **When adding a new error:**
    - Ask: Is this error user-facing? Does it need custom language or localization?
      - If yes, add a template to the registry.
      - If no, add to code-based errors.
2. **Document any new registry templates and their placeholders.**
3. **Add/modify tests** to cover the new error path.

---

## Code Comments and Documentation

- In `error_renderer.py`, add docstrings/comments explaining the lookup order and rationale.
- Example:
  ```python
  """
  Error rendering order:
    1. Try to load a registry/template-based message for the error type.
    2. If not found, use the code-based generic message.
  Use registry for user-facing, customizable, or localized errors.
  Use code for simple, generic, or internal errors.
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
