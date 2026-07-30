"""Surface parked unsupported AST nodes as semantic warnings."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class UnsupportedSyntaxRule:
    """Promote UnsupportedStatementNode entries to semantic warnings."""

    @property
    def name(self) -> str:
        return "unsupported_syntax"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for node in ast.unsupported:
            diagnostics.append(
                diagnostic(
                    code=DiagnosticCode.W_SEM_UNSUPPORTED,
                    severity=Severity.WARNING,
                    message=(
                        f"Unsupported application statement '{node.keyword}' "
                        f"requires manual review: {node.reason}"
                    ),
                    span=node.span,
                    application=ast.name,
                    hint=node.raw,
                )
            )
        for job in ast.jobs:
            for node in job.unsupported:
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.W_SEM_UNSUPPORTED,
                        severity=Severity.WARNING,
                        message=(
                            f"Unsupported statement '{node.keyword}' in job "
                            f"'{job.name}' requires manual review."
                        ),
                        span=node.span,
                        application=ast.name,
                        job=job.name,
                        hint=node.raw,
                    )
                )
        return diagnostics
