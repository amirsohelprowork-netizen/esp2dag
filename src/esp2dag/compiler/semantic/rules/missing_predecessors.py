"""Detect missing dependency / release targets."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import (
    diagnostic,
    is_external_job,
    is_runtime_symbol,
    job_index,
)
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class MissingPredecessorRule:
    """Validate dependency endpoints against jobs declared in the application.

    RELEASE targets name downstream jobs. AFTER-style predecessors name upstream
    jobs. Runtime symbols (containing ``!``) and EXTERNAL jobs are exempt from
    hard errors.
    """

    @property
    def name(self) -> str:
        return "missing_predecessors"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        jobs = job_index(ast)
        diagnostics: list[Diagnostic] = []

        for job in ast.jobs:
            for dep in job.dependencies:
                target = dep.predecessor
                if not target or target in jobs or is_runtime_symbol(target):
                    continue
                # Strip optional (A)/(N) qualifier for lookup.
                bare = target.split("(", 1)[0]
                if bare in jobs or is_runtime_symbol(bare):
                    continue

                kind = (dep.dependency_type or "AFTER").upper()
                if kind == "RELEASE":
                    # Downstream may live in another application.
                    diagnostics.append(
                        diagnostic(
                            code=DiagnosticCode.E_SEM_MISSING_PRED,
                            severity=Severity.WARNING,
                            message=(
                                f"RELEASE target '{target}' from job '{job.name}' "
                                f"is not defined in application '{ast.name}'."
                            ),
                            span=dep.span or job.span,
                            application=ast.name,
                            job=job.name,
                            hint="Verify the successor job name or cross-application link.",
                        )
                    )
                else:
                    if is_external_job(job):
                        continue
                    diagnostics.append(
                        diagnostic(
                            code=DiagnosticCode.E_SEM_MISSING_PRED,
                            severity=Severity.ERROR,
                            message=(
                                f"Predecessor '{target}' referenced by job '{job.name}' "
                                f"is not defined in application '{ast.name}'."
                            ),
                            span=dep.span or job.span,
                            application=ast.name,
                            job=job.name,
                            hint="Declare the predecessor job or mark the reference EXTERNAL.",
                        )
                    )
        return diagnostics
