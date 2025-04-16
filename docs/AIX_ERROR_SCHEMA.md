# FHIR Nudge AIX Error Schema

This document describes the **AI Experience (AIX) Error Schema** used by the FHIR Nudge proxy to provide rich, actionable, and LLM-friendly error responses.

## Purpose

The AIX Error Schema is designed to:
- Make FHIR errors more understandable and actionable for both humans and AI tools (LLMs).
- Provide structured, consistent, and extensible error information for all API consumers.
- Enable downstream tools to chain actions or suggest next steps based on error context.

## Why AIX?

Traditional FHIR errors are highly technical and often hard for end-users or AI agents to interpret. The AIX schema bridges this gap by providing both technical detail and human/AI-friendly guidance in every error response.

## Extensibility

This schema is designed to be extended as new endpoints and error scenarios are added. For example, future fields could include:
- `llm_hint` or `tool_hint` (explicit guidance for AI tools)
- `original_fhir_response` (for debugging)
- `timestamp`, etc.

---

For implementation details, see the proxy code and associated tests.

## Schema Structure (Example)

```
{
  "error": "Resource not found",
  "friendly_message": "No Patient resource was found with ID '123'. Double-check the ID or try searching for patients.",
  "next_steps": "Try using /searchResource with patient demographics to locate the correct patient ID.",
  "resource_type": "Patient",
  "resource_id": "123",
  "status_code": 404,
  "issues": [
    {
      "severity": "error",
      "code": "not-found",
      "diagnostics": "No resource found with id 123"
    }
  ]
}
```

### Field Descriptions

- `error`: A short, machine-readable error summary.
- `friendly_message`: A plain-language explanation of what went wrong, suitable for direct display to users or LLMs.
- `next_steps`: (Optional) Suggestions for how to resolve or proceed after the error.
- `resource_type`: (Optional) The FHIR resource type involved in the error.
- `resource_id`: (Optional) The specific resource ID requested.
- `status_code`: The HTTP status code returned.
- `issues`: (Optional) List of structured FHIR OperationOutcome issues, if available.


