from typing import List, Optional
from pydantic import BaseModel

class OperationOutcomeIssue(BaseModel):
    severity: Optional[str]
    code: Optional[str]
    diagnostics: Optional[str]
    details: Optional[str]

class AIXErrorResponse(BaseModel):
    error: str
    friendly_message: str
    next_steps: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status_code: int
    issues: List[OperationOutcomeIssue] = []
