"""Mermaid flowchart renderer for Workflow IR."""

from __future__ import annotations

from esp2dag.models.workflow import Workflow
from esp2dag.yaml_generator.operators import resolve_operator


def render_mermaid(workflow: Workflow) -> str:
    """Render a Mermaid ``flowchart TD`` for one workflow."""
    lines = [
        f"%% workflow: {workflow.id}",
        "flowchart TD",
    ]
    for task in workflow.tasks:
        node_id = _safe_id(task.task_id)
        esp = task.params.get("esp_job_type") or task.task_type.value
        label = _escape(f"{task.task_id}<br/>{esp}")
        lines.append(f'  {node_id}["{label}"]')

    for dep in workflow.dependencies:
        up = _safe_id(dep.upstream_task_id)
        down = _safe_id(dep.downstream_task_id)
        lines.append(f"  {up} --> {down}")

    if not workflow.tasks:
        lines.append('  empty["(no tasks)"]')

    # Keep operator hint as comment for tooling.
    for task in workflow.tasks:
        op = resolve_operator(task).rsplit(".", 1)[-1]
        lines.append(f"  %% {task.task_id} -> {op}")

    return "\n".join(lines) + "\n"


def _safe_id(task_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in task_id)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned


def _escape(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")
