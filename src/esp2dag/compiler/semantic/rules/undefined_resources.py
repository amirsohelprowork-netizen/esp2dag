"""Detect resource references without in-app definitions (advisory)."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class UndefinedResourceRule:
    """Warn when RESOURCE ADD names are not declared at application scope.

    ESP often uses globally defined resources, so this is a WARNING, not ERROR.
    """

    @property
    def name(self) -> str:
        return "undefined_resources"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        defined = {r.name.upper() for r in ast.resources}
        if not defined:
            # No local catalog — skip noisy warnings for typical ESP extracts.
            return []

        diagnostics: list[Diagnostic] = []
        for job in ast.jobs:
            for ref in job.resources:
                if ref.name.upper() in defined:
                    continue
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_UNDEFINED_RESOURCE,
                        severity=Severity.WARNING,
                        message=(
                            f"Resource '{ref.name}' used by job '{job.name}' "
                            f"is not declared in application '{ast.name}'."
                        ),
                        span=ref.span,
                        application=ast.name,
                        job=job.name,
                    )
                )
        return diagnostics
