"""Minimal Workflow IR validator."""

from __future__ import annotations

from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity
from esp2dag.models.workflow import Workflow

STAGE = "validator"


class WorkflowValidator:
    """Validate enriched Workflow IR before generation."""

    def validate(self, workflow: Workflow) -> list[Diagnostic]:
        """Return diagnostics for one workflow."""
        diagnostics: list[Diagnostic] = []
        if not workflow.tasks:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.W_WF_MANUAL_REVIEW,
                    severity=Severity.WARNING,
                    message=f"Workflow '{workflow.id}' has no tasks.",
                    stage=STAGE,
                    application=workflow.name,
                    hint="empty_workflow",
                )
            )

        known = {t.task_id for t in workflow.tasks}
        for dep in workflow.dependencies:
            for endpoint, role in (
                (dep.upstream_task_id, "upstream"),
                (dep.downstream_task_id, "downstream"),
            ):
                if endpoint not in known:
                    diagnostics.append(
                        Diagnostic(
                            code=DiagnosticCode.E_WF_INVALID,
                            severity=Severity.WARNING,
                            message=(
                                f"Dependency {role} '{endpoint}' not found in "
                                f"workflow '{workflow.id}'."
                            ),
                            stage=STAGE,
                            application=workflow.name,
                        )
                    )
        return diagnostics
