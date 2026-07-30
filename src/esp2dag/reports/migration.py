"""Migration readiness report builders."""

from __future__ import annotations

from collections import Counter
from typing import Any

from esp2dag.models.config import CompileResult
from esp2dag.yaml_generator.operators import (
    AS400_OPERATOR,
    MAINFRAME_DATASET_SENSOR,
    MAINFRAME_OPERATOR,
    resolve_operator,
)

_CUSTOM_OPS = frozenset({AS400_OPERATOR, MAINFRAME_OPERATOR, MAINFRAME_DATASET_SENSOR})


def build_migration(result: CompileResult) -> dict[str, Any]:
    """Per-application migration readiness summary."""
    id_counts: Counter[str] = Counter(wf.id for wf in result.workflows)
    colliding = sorted(dag_id for dag_id, n in id_counts.items() if n > 1)

    apps: list[dict[str, Any]] = []
    custom_needed: Counter[str] = Counter()

    for wf in result.workflows:
        ops = Counter(resolve_operator(t) for t in wf.tasks)
        customs = sorted(op for op in ops if op in _CUSTOM_OPS)
        for op in customs:
            custom_needed[op] += ops[op]
        unsupported = sorted(
            {feat for t in wf.tasks for feat in t.unsupported_features}
        )
        apps.append(
            {
                "workflow_id": wf.id,
                "name": wf.name,
                "task_count": len(wf.tasks),
                "dependency_count": len(wf.dependencies),
                "schedule": (wf.schedule.cron if wf.schedule and wf.schedule.cron else None)
                or (wf.schedule.raw_expression if wf.schedule else None),
                "schedule_status": wf.schedule.mapping_status.value if wf.schedule else None,
                "custom_operators": customs,
                "unsupported_features": unsupported,
                "operator_mix": dict(ops),
                "colliding_id": id_counts[wf.id] > 1,
            }
        )

    apps.sort(key=lambda a: a["workflow_id"])
    return {
        "applications": apps,
        "colliding_dag_ids": colliding,
        "custom_operators_required": dict(custom_needed.most_common()),
        "manual_review_count": sum(
            1
            for a in apps
            if a["unsupported_features"] or a["colliding_id"] or a["custom_operators"]
        ),
    }


def migration_markdown(data: dict[str, Any]) -> str:
    """Render migration readiness as Markdown."""
    lines = [
        "# Migration Report",
        "",
        f"- Applications summarized: **{len(data.get('applications', []))}**",
        f"- Manual review suggested: **{data.get('manual_review_count', 0)}**",
        f"- Colliding DAG ids: **{len(data.get('colliding_dag_ids', []))}**",
        "",
        "## Custom operators required",
        "",
    ]
    customs = data.get("custom_operators_required") or {}
    if not customs:
        lines.append("- (none)")
    else:
        for op, count in customs.items():
            lines.append(f"- `{op}`: {count} task(s)")

    collisions = data.get("colliding_dag_ids") or []
    lines.extend(["", "## Colliding DAG ids", ""])
    if not collisions:
        lines.append("- (none)")
    else:
        for dag_id in collisions:
            lines.append(f"- `{dag_id}`")

    lines.extend(["", "## Applications needing attention", ""])
    attention = [
        a
        for a in data.get("applications", [])
        if a["unsupported_features"] or a["colliding_id"] or a["custom_operators"]
    ][:50]
    if not attention:
        lines.append("- (none in top slice)")
    else:
        for app in attention:
            reasons = []
            if app["custom_operators"]:
                reasons.append("custom ops")
            if app["unsupported_features"]:
                reasons.append("unsupported")
            if app["colliding_id"]:
                reasons.append("id collision")
            lines.append(f"- `{app['workflow_id']}`: {', '.join(reasons)}")
    lines.append("")
    return "\n".join(lines)
