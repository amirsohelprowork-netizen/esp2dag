"""Structured compiler diagnostics."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.models.source import SourceSpan


class Severity(StrEnum):
    """Diagnostic severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Diagnostic(BaseModel):
    """One structured diagnostic produced by any compiler stage."""

    model_config = ConfigDict(frozen=True)

    code: str
    severity: Severity
    message: str
    stage: str
    span: SourceSpan | None = None
    application: str | None = None
    job: str | None = None
    hint: str | None = None


class FailedUnit(BaseModel):
    """An application (or other unit) that failed at a specific stage."""

    model_config = ConfigDict(frozen=True)

    unit_id: str
    stage: str
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    span: SourceSpan | None = None
    exception_type: str | None = None
    exception_message: str | None = None


# Stable diagnostic code registry (extend as stages are implemented).
class DiagnosticCode:
    """Well-known diagnostic codes."""

    # Extractor
    E_EXTRACT_UNCLOSED_APP = "E100"
    E_EXTRACT_ORPHAN_ENDAPPL = "E101"
    E_EXTRACT_NO_APPS = "E102"
    W_EXTRACT_EMPTY_APP = "W100"
    W_EXTRACT_PROLOGUE = "W101"
    W_EXTRACT_DUPLICATE_NAME = "W102"
    W_EXTRACT_INTERSTITIAL = "W103"

    # Lexer
    E_LEX_UNEXPECTED_CHAR = "E200"
    W_LEX_UNKNOWN_KEYWORD = "W200"

    # Parser
    E_PARSE_UNEXPECTED_TOKEN = "E300"
    E_PARSE_MISSING_TOKEN = "E301"
    W_PARSE_UNSUPPORTED = "W300"

    # Semantic
    E_SEM_DUPLICATE_JOB = "E400"
    E_SEM_DUPLICATE_APP = "E401"
    E_SEM_CIRCULAR_DEP = "E402"
    E_SEM_MISSING_PRED = "E403"
    E_SEM_UNDEFINED_RESOURCE = "E404"
    E_SEM_INVALID_SCHEDULE = "E405"
    E_SEM_INVALID_REF = "E406"
    W_SEM_UNSUPPORTED = "W400"

    # IR / validator
    W_IR_EMPTY_WORKFLOW = "W500"
    W_IR_DANGLING_EDGE = "W501"

    # Events
    W_EVENT_UNBOUND = "W600"
    W_EVENT_UNMAPPED = "W601"

    # Events
    E_EVENT_PARSE = "E500"
    W_EVENT_UNMAPPED = "W500"
    W_EVENT_ORPHAN = "W501"

    # Workflow / validation
    E_WF_INVALID = "E600"
    W_WF_MANUAL_REVIEW = "W600"

    # Generators
    W_YAML_PARTIAL_SCHEDULE = "W700"
    W_AIRFLOW_UNSUPPORTED_TASK = "W800"
