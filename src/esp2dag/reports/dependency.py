"""Cross-DAG dependency report builders."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from esp2dag.models.config import CompileResult
from esp2dag.yaml_generator.operators import EXTERNAL_SENSOR, resolve_operator


def build_dependencies(result: CompileResult) -> dict[str, Any]:
    """Map ExternalTaskSensor edges across workflows."""
    producers: dict[str, list[dict[str, str]]] = defaultdict(list)
    consumers: list[dict[str, str]] = []

    for wf in result.workflows:
        for task in wf.tasks:
            if resolve_operator(task) != EXTERNAL_SENSOR:
                continue
            external_dag = (
                task.params.get("external_dag_id")
                or (task.sensor.external_dag_id if task.sensor else None)
                or "unknown"
            ).lower()
            external_task = task.name
            entry = {
                "consumer_dag": wf.id,
                "consumer_task": task.task_id,
                "external_dag_id": external_dag,
                "external_task_id": external_task,
            }
            consumers.append(entry)
            producers[external_dag].append(entry)

    known = {wf.id for wf in result.workflows}
    missing_targets = sorted(
        dag_id for dag_id in producers if dag_id not in known and dag_id != "unknown"
    )

    return {
        "external_edges": sorted(
            consumers, key=lambda e: (e["consumer_dag"], e["consumer_task"])
        ),
        "by_external_dag": {
            dag: edges for dag, edges in sorted(producers.items(), key=lambda kv: kv[0])
        },
        "missing_external_dags": missing_targets,
        "edge_count": len(consumers),
    }
