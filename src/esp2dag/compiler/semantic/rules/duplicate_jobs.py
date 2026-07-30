"""Detect duplicate job names within an application."""

from __future__ import annotations

from collections import defaultdict

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class DuplicateJobRule:
    """Flag jobs declared more than once in the same application."""

    @property
    def name(self) -> str:
        return "duplicate_jobs"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        by_name: dict[str, list[int]] = defaultdict(list)
        for index, job in enumerate(ast.jobs):
            by_name[job.name].append(index)

        diagnostics: list[Diagnostic] = []
        for job_name, indexes in by_name.items():
            if len(indexes) < 2:
                continue
            first = ast.jobs[indexes[0]]
            for dup_index in indexes[1:]:
                dup = ast.jobs[dup_index]
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_DUPLICATE_JOB,
                        severity=Severity.ERROR,
                        message=(
                            f"Duplicate job '{job_name}' in application '{ast.name}' "
                            f"(first at line {first.span.start_line})."
                        ),
                        span=dup.span,
                        application=ast.name,
                        job=job_name,
                        hint="Rename or remove the duplicate job declaration.",
                    )
                )
        return diagnostics
