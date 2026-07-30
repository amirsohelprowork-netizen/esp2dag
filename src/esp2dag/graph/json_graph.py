"""JSON dependency graph renderer for Workflow IR."""

from __future__ import annotations

import json
from typing import Any

from esp2dag.models.workflow import Workflow
from esp2dag.yaml_generator.operators import resolve_operator


def render_json_graph(workflow: Workflow) -> str:
    """Render a JSON node/edge graph for one workflow."""
    nodes: list[dict[str, Any]] = []
    for task in workflow.tasks:
        nodes.append(
            {
                "id": task.task_id,
                "name": task.name,
                "esp_job_type": task.params.get("esp_job_type"),
                "task_type": task.task_type.value,
                "operator": resolve_operator(task),
            }
        )
    edges = [
        {
            "from": dep.upstream_task_id,
            "to": dep.downstream_task_id,
            "kind": dep.kind.value,
        }
        for dep in workflow.dependencies
    ]
    payload = {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "nodes": nodes,
        "edges": edges,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
