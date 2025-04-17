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
      "diagnostics": "No resource found with id 123",
      "details": null
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
- `details`: (Optional) Additional structured details for each issue, suitable for machine consumption.

## Contract for Error Generation

- **App code must supply all actionable context** (diagnostics, resource type, resource ID, etc.) when calling the error renderer.
- **The error renderer only formats and standardizes**; it does not invent or deduce diagnostics.
- **All actionable information appears in the `issues` array**, specifically in the `diagnostics` field.
- **No top-level ad-hoc fields** (e.g., `supported_types`, `did_you_mean`); suggestions and context are embedded in diagnostics.

## Example Error Response

```json
{
  "error": "Invalid type",
  "friendly_message": "Resource type 'NotAType' is not supported.",
  "next_steps": "Try a supported resource type.",
  "resource_type": "NotAType",
  "resource_id": "123",
  "status_code": 400,
  "issues": [
    {
      "severity": "error",
      "code": "invalid-type",
      "diagnostics": "Resource type 'NotAType' is not supported. Supported types: ['Patient', 'Observation']. Did you mean: 'Patient'?",
      "details": null
    }
  ]
}
```

## Best Practices

- Always provide as much context as possible in diagnostics.
- Use the renderer for message consistency, not for generating core error content.
