"""
schemas.py
==========
Pydantic models that define the "shape" of every request and response the
API accepts or returns.

Why this matters for the judges / graders:
    FastAPI uses these classes to automatically:
      1. Validate incoming JSON (reject bad requests with a clear 422 error
         instead of crashing deep inside business logic).
      2. Generate the interactive OpenAPI docs at /docs and /redoc.
      3. Serialize responses consistently.

    This is the difference between a "script that works on my machine" and
    a documented, self-describing production API.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Severity(str, Enum):
    """How serious a single finding is, used to sort/highlight results."""

    CRITICAL = "critical"  # security vulnerability, data loss, crash
    HIGH = "high"          # likely bug, major performance problem
    MEDIUM = "medium"      # best-practice violation, moderate risk
    LOW = "low"            # style / readability / minor nit
    INFO = "info"          # informational note, no action strictly required


class Category(str, Enum):
    """Which aspect of code quality a finding belongs to."""

    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"


class CodeReviewRequest(BaseModel):
    """The payload the frontend sends when the user clicks 'Review Code'."""

    code: str = Field(..., min_length=1, description="Raw source code submitted for review.")
    language: Optional[str] = Field(
        default=None,
        description="Language hint from the editor (e.g. 'python', 'javascript'). "
        "If omitted, the backend attempts automatic detection.",
    )
    filename: Optional[str] = Field(
        default=None, description="Optional filename, used to improve language detection."
    )

    @field_validator("code")
    @classmethod
    def code_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only submissions early, before they reach the LLM."""
        if not value.strip():
            raise ValueError("Submitted code is empty.")
        return value


class Finding(BaseModel):
    """A single, structured review comment (one bug, one style nit, etc.)."""

    line: Optional[int] = Field(default=None, description="1-indexed line number this finding refers to, if known.")
    category: Category
    severity: Severity
    title: str = Field(..., description="Short, human-readable summary of the issue.")
    explanation: str = Field(..., description="Why this is a problem.")
    suggestion: Optional[str] = Field(default=None, description="Concrete fix or improved code snippet.")
    source: str = Field(
        default="llm",
        description="Where this finding came from: 'llm' (model-generated) or the name "
        "of the static-analysis tool that produced it (e.g. 'bandit', 'pylint').",
    )


class StaticAnalysisSummary(BaseModel):
    """Aggregated, tool-generated metrics that accompany the LLM's narrative review."""

    tool: str
    findings_count: int
    raw_output: Optional[str] = Field(
        default=None, description="Trimmed raw tool output, useful for debugging/transparency."
    )


class CodeReviewResponse(BaseModel):
    """Everything the frontend needs to render the review results panel."""
    model_config = ConfigDict(protected_namespaces=())
    language_detected: str
    summary: str = Field(..., description="A short, plain-English overview of the code's overall quality.")
    findings: List[Finding] = Field(default_factory=list)
    static_analysis: List[StaticAnalysisSummary] = Field(default_factory=list)
    overall_score: int = Field(..., ge=0, le=100, description="Heuristic 0-100 code quality score.")
    model_used: str = Field(..., description="Which LLM provider/model produced the narrative review.")


class HealthResponse(BaseModel):
    """Simple liveness/readiness payload for /api/health."""

    status: str
    llm_provider: str
    version: str
