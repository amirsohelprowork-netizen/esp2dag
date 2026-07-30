"""Warn on applications with no jobs."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class EmptyApplicationRule:
    """Flag applications that contain no job definitions."""

    @property
    def name(self) -> str:
        return "empty_application"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        if ast.jobs:
            return []
        return [
            diagnostic(
                code=DiagnosticCode.W_SEM_UNSUPPORTED,
                severity=Severity.WARNING,
                message=f"Application '{ast.name}' contains no jobs.",
                span=ast.span,
                application=ast.name,
                hint="Confirm the APPL body was extracted and parsed correctly.",
            )
        ]
