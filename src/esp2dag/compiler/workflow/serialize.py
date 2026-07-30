"""Workflow IR serialization for CLI and golden tests."""

from __future__ import annotations

from esp2dag.models.workflow import Workflow


def workflow_summary(workflow: Workflow) -> dict[str, object]:
    """Compact deterministic summary of a Workflow IR."""
    return {
        "id": workflow.id,
        "name": workflow.name,
        "task_count": len(workflow.tasks),
        "dependency_count": len(workflow.dependencies),
        "tasks": [
            {
                "task_id": t.task_id,
                "name": t.name,
                "task_type": t.task_type.value,
                "command": t.command,
                "pool": t.pool,
                "source_line": t.trace.source_line,
                "unsupported_features": list(t.unsupported_features),
            }
            for t in workflow.tasks
        ],
        "dependencies": [
            {
                "upstream": d.upstream_task_id,
                "downstream": d.downstream_task_id,
                "kind": d.kind.value,
            }
            for d in workflow.dependencies
        ],
        "schedule": (
            {
                "raw": workflow.schedule.raw_expression,
                "cron": workflow.schedule.cron,
                "status": workflow.schedule.mapping_status.value,
            }
            if workflow.schedule
            else None
        ),
        "tags": list(workflow.metadata.tags),
        "event_count": len(workflow.events),
        "notification_count": len(workflow.notifications),
    }
