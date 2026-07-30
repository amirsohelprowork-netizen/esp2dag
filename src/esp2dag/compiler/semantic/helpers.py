"""Shared helpers for semantic rules."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode, JobNode
from esp2dag.models.diagnostics import Diagnostic, Severity
from esp2dag.models.source import SourceSpan

STAGE = "semantic"


def job_index(ast: ApplicationNode) -> dict[str, JobNode]:
    """Map job name → first JobNode (declaration order)."""
    index: dict[str, JobNode] = {}
    for job in ast.jobs:
        if job.name not in index:
            index[job.name] = job
    return index


def is_external_job(job: JobNode) -> bool:
    """True when job is marked EXTERNAL."""
    return any(m.key == "external" for m in job.metadata)


def is_runtime_symbol(name: str) -> bool:
    """Symbolic ESP names resolved at runtime (e.g. LIS.!ESPAPPL)."""
    return "!" in name


def diagnostic(
    *,
    code: str,
    severity: Severity,
    message: str,
    span: SourceSpan | None,
    application: str | None = None,
    job: str | None = None,
    hint: str | None = None,
) -> Diagnostic:
    """Build a semantic-stage diagnostic."""
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        stage=STAGE,
        span=span,
        application=application,
        job=job,
        hint=hint,
    )
