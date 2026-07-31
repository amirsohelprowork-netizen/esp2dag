"""Graphviz DOT renderer for Workflow IR (text only — no graphviz binary)."""

from __future__ import annotations

from esp2dag.models.workflow import Workflow
from esp2dag.yaml_generator.operators import resolve_operator


def render_graphviz(workflow: Workflow) -> str:
    """Render a DOT digraph for one workflow."""
    lines = [
        f'digraph "{_escape(workflow.id)}" {{',
        "  rankdir=TB;",
        '  node [shape=box, fontname="Helvetica"];',
    ]
    known_ids = {task.task_id for task in workflow.tasks}
    for task in workflow.tasks:
        esp = task.params.get("esp_job_type") or task.task_type.value
        op = resolve_operator(task).rsplit(".", 1)[-1]
        label = f"{task.task_id}\\n{esp}\\n{op}"
        lines.append(f'  "{_escape(task.task_id)}" [label="{label}"];')

    unresolved_ids = sorted(
        {
            endpoint
            for dep in workflow.dependencies
            for endpoint in (dep.upstream_task_id, dep.downstream_task_id)
            if endpoint not in known_ids
        }
    )
    for task_id in unresolved_ids:
        lines.append(
            f'  "{_escape(task_id)}" [label="UNRESOLVED\\n{_escape(task_id)}", '
            'color="#cc0000", fontcolor="#cc0000", style="dashed"];'
        )

    for dep in workflow.dependencies:
        attrs: list[str] = []
        if dep.condition:
            attrs.append(f'label="{_escape(dep.condition)}"')
        if dep.kind.value != "success":
            attrs.extend(['color="#cc6600"', 'style="dashed"'])
        suffix = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(
            f'  "{_escape(dep.upstream_task_id)}" -> "{_escape(dep.downstream_task_id)}"{suffix};'
        )

    if not workflow.tasks:
        lines.append('  empty [label="(no tasks)"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
