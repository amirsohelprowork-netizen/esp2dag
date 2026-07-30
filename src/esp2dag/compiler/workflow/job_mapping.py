"""Map ESP AST job kinds onto Workflow TaskType / sensors."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import JobNode
from esp2dag.models.workflow import SensorSpec, TaskType


def map_task_type(job: JobNode) -> tuple[TaskType, SensorSpec | None, list[str]]:
    """Infer IR task type, optional sensor, and unsupported feature flags."""
    unsupported: list[str] = []
    job_type = (job.job_type or "JOB").upper()
    external = any(m.key == "external" for m in job.metadata)
    has_command = bool(job.command and job.command.text.strip())
    is_link = any(m.key == "link" for m in job.metadata)
    is_task = any(m.key == "task" for m in job.metadata)

    if external or job.event_refs:
        sensor = SensorSpec(
            sensor_type="external_task",
            external_dag_id=job.event_refs[0].event_name if job.event_refs else None,
            external_task_id=None,
        )
        return TaskType.SENSOR_EXTERNAL, sensor, unsupported

    if job_type in {"FILE_TRIGGER", "DSTRIG"}:
        filepath = meta_value(job, "dsname") or meta_value(job, "filename")
        sensor = SensorSpec(sensor_type="file", filepath=filepath)
        return TaskType.SENSOR_FILE, sensor, unsupported

    if job_type in {"DATA_OBJECT", "AGENT_MONITOR"}:
        return TaskType.PYTHON, None, unsupported

    if is_link or is_task or job_type in {"APPLEND", "LINK_JOB"}:
        return TaskType.EMPTY, None, unsupported

    if job_type == "SAP_JOB":
        return TaskType.BASH, None, unsupported

    if job_type == "JOB":
        # Standard z/OS batch (CCCHK / JCL) — generator maps to mainframe operator.
        return TaskType.BASH, None, unsupported

    if job_type.endswith("_JOB"):
        if has_command:
            return TaskType.BASH, None, unsupported
        return TaskType.EMPTY, None, unsupported

    unsupported.append(f"job_type:{job_type}")
    if has_command:
        return TaskType.BASH, None, unsupported
    return TaskType.UNKNOWN, None, unsupported


def meta_value(job: JobNode, key: str) -> str | None:
    """Return the first metadata value for ``key``, if present."""
    for item in job.metadata:
        if item.key == key and item.value:
            return item.value
    return None
