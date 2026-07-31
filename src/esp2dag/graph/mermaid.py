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
    known_ids = {task.task_id for task in workflow.tasks}
    for task in workflow.tasks:
        node_id = _safe_id(task.task_id)
        esp = task.params.get("esp_job_type") or task.task_type.value
        label = _escape(f"{task.task_id}<br/>{esp}")
        lines.append(f'  {node_id}["{label}"]')

    unresolved_ids = sorted(
        {
            endpoint
            for dep in workflow.dependencies
            for endpoint in (dep.upstream_task_id, dep.downstream_task_id)
            if endpoint not in known_ids
        }
    )
    for task_id in unresolved_ids:
        node_id = _missing_id(task_id)
        lines.append(f'  {node_id}["❗ UNRESOLVED<br/>{_escape(task_id)}"]')
        lines.append(f"  class {node_id} unresolved;")

    for dep in workflow.dependencies:
        up = (
            _safe_id(dep.upstream_task_id)
            if dep.upstream_task_id in known_ids
            else _missing_id(dep.upstream_task_id)
        )
        down = (
            _safe_id(dep.downstream_task_id)
            if dep.downstream_task_id in known_ids
            else _missing_id(dep.downstream_task_id)
        )
        label = _edge_label(dep.kind.value, dep.condition)
        lines.append(f"  {up} -->|{label}| {down}" if label else f"  {up} --> {down}")

    if not workflow.tasks:
        lines.append('  empty["(no tasks)"]')

    # Keep operator hint as comment for tooling.
    for task in workflow.tasks:
        op = resolve_operator(task).rsplit(".", 1)[-1]
        lines.append(f"  %% {task.task_id} -> {op}")

    if unresolved_ids:
        lines.append("  classDef unresolved fill:#ffe5e5,stroke:#d33,stroke-width:2px;")

    return "\n".join(lines) + "\n"


def _safe_id(task_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in task_id)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned


def _missing_id(task_id: str) -> str:
    return f"missing_{_safe_id(task_id)}"


def _edge_label(kind: str, condition: str | None) -> str:
    parts = []
    if kind != "success":
        parts.append(kind.upper())
    if condition:
        parts.append(condition)
    return _escape("; ".join(parts))


def _escape(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")
