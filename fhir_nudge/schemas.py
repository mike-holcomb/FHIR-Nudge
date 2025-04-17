"""Pydantic models for AI Experience (AIX) error schema.

Defines OperationOutcomeIssue and AIXErrorResponse per docs/AIX_ERROR_SCHEMA.md.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class OperationOutcomeIssue(BaseModel):
    """
    Represents a single FHIR OperationOutcome issue.

    severity: issue severity (e.g., 'error', 'warning').
    code: machine-readable issue code (e.g., 'not-found').
    diagnostics: human-/AI-friendly explanation of the issue.
    details: optional structured details for machine processing.
    """
    severity: Optional[str] = Field(None, description="Issue severity (e.g., 'error', 'warning').")
    code: Optional[str] = Field(None, description="Machine-readable issue code (e.g., 'not-found').")
    diagnostics: Optional[str] = Field(None, description="Human-/AI-friendly explanation of the issue.")
    details: Optional[str] = Field(None, description="Optional structured details suitable for machine consumption.")

    # Pydantic v2 model config: use ConfigDict for json_schema_extra
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "severity": "error",
                "code": "not-found",
                "diagnostics": "No resource found with id 123",
                "details": None
            }
        }
    )

class AIXErrorResponse(BaseModel):
    """
    Top-level error response model following the AIX schema.

    error: short error summary.
    friendly_message: user-/AI-friendly explanation.
    next_steps: optional remediation guidance.
    resource_type: FHIR resource type involved.
    resource_id: specific FHIR resource ID.
    status_code: HTTP status code of the error.
    issues: list of OperationOutcomeIssue instances.
    """
    error: str = Field(..., description="Short, machine-readable error summary.")
    friendly_message: str = Field(..., description="Plain-language explanation for users or AI.")
    next_steps: Optional[str] = Field(None, description="Suggestions for resolving or proceeding after the error.")
    resource_type: Optional[str] = Field(None, description="FHIR resource type involved in the error.")
    resource_id: Optional[str] = Field(None, description="Specific FHIR resource ID requested.")
    status_code: int = Field(..., description="HTTP status code returned by the operation.")
    issues: List[OperationOutcomeIssue] = Field(default_factory=list, description="List of detailed issue objects.")

    # Pydantic v2 model config: use ConfigDict for json_schema_extra
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                        "details": None
                    }
                ]
            }
        }
    )
