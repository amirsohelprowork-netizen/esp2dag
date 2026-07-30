"""Validate APPLID / event-style references on jobs."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic, is_external_job
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class InvalidReferenceRule:
    """Check EXTERNAL/APPLID consistency."""

    @property
    def name(self) -> str:
        return "invalid_references"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for job in ast.jobs:
            has_applid = bool(job.event_refs)
            external = is_external_job(job)
            if has_applid and not external:
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_INVALID_REF,
                        severity=Severity.WARNING,
                        message=(
                            f"Job '{job.name}' has APPLID but is not marked EXTERNAL."
                        ),
                        span=job.event_refs[0].span,
                        application=ast.name,
                        job=job.name,
                        hint="Add EXTERNAL or remove APPLID if not an external reference.",
                    )
                )
            if external and not has_applid:
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_INVALID_REF,
                        severity=Severity.WARNING,
                        message=(
                            f"Job '{job.name}' is EXTERNAL but has no APPLID reference."
                        ),
                        span=job.span,
                        application=ast.name,
                        job=job.name,
                    )
                )
        return diagnostics
