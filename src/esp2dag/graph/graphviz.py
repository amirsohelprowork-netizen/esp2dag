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
    for task in workflow.tasks:
        esp = task.params.get("esp_job_type") or task.task_type.value
        op = resolve_operator(task).rsplit(".", 1)[-1]
        label = f"{task.task_id}\\n{esp}\\n{op}"
        lines.append(f'  "{_escape(task.task_id)}" [label="{label}"];')

    for dep in workflow.dependencies:
        lines.append(
            f'  "{_escape(dep.upstream_task_id)}" -> "{_escape(dep.downstream_task_id)}";'
        )

    if not workflow.tasks:
        lines.append('  empty [label="(no tasks)"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
