"""Statistics report builders."""

from __future__ import annotations

from collections import Counter
from typing import Any

from esp2dag.models.config import CompileResult
from esp2dag.models.workflow import MappingStatus
from esp2dag.yaml_generator.operators import resolve_operator


def build_statistics(result: CompileResult) -> dict[str, Any]:
    """Aggregate compile statistics including operator mix."""
    operators: Counter[str] = Counter()
    schedules: Counter[str] = Counter()
    mapped_schedules = 0
    raw_schedules = 0
    unsupported = 0

    for wf in result.workflows:
        for task in wf.tasks:
            operators[resolve_operator(task)] += 1
            unsupported += len(task.unsupported_features)
        if wf.schedule is None:
            continue
        cron = wf.schedule.cron or wf.schedule.raw_expression or ""
        schedules[cron] += 1
        if wf.schedule.mapping_status == MappingStatus.MAPPED:
            mapped_schedules += 1
        else:
            raw_schedules += 1

    stats = result.statistics
    return {
        "total_applications": stats.total_applications or len(result.workflows) + len(result.failures),
        "successful_conversions": stats.successful_conversions or len(result.workflows),
        "failed_conversions": stats.failed_conversions or len(result.failures),
        "total_jobs": stats.total_jobs or sum(len(w.tasks) for w in result.workflows),
        "total_dependencies": stats.total_dependencies
        or sum(len(w.dependencies) for w in result.workflows),
        "total_events": stats.total_events or sum(len(w.events) for w in result.workflows),
        "warnings": stats.warnings,
        "errors": stats.errors,
        "unsupported_features": unsupported,
        "mapped_schedules": mapped_schedules,
        "unmapped_or_partial_schedules": raw_schedules,
        "operator_mix": dict(operators.most_common()),
        "schedule_samples": dict(schedules.most_common(20)),
    }


def statistics_markdown(data: dict[str, Any]) -> str:
    """Render statistics as Markdown."""
    lines = [
        "# Compile Statistics",
        "",
        f"- Applications: **{data['total_applications']}**",
        f"- Successful: **{data['successful_conversions']}**",
        f"- Failed: **{data['failed_conversions']}**",
        f"- Jobs/tasks: **{data['total_jobs']}**",
        f"- Dependencies: **{data['total_dependencies']}**",
        f"- Events: **{data['total_events']}**",
        f"- Warnings: **{data['warnings']}** / Errors: **{data['errors']}**",
        f"- Mapped schedules: **{data['mapped_schedules']}**",
        f"- Partial/raw schedules: **{data['unmapped_or_partial_schedules']}**",
        "",
        "## Operator mix",
        "",
    ]
    for op, count in data.get("operator_mix", {}).items():
        lines.append(f"- `{op}`: {count}")
    lines.append("")
    return "\n".join(lines)
