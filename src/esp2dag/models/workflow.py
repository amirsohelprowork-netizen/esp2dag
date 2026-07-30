"""Intermediate Workflow Model — scheduler-independent IR.

Downstream of WorkflowBuilder, stages must consume only these types
(plus diagnostics/config). No AST or ESP token imports.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.models.diagnostics import Diagnostic
from esp2dag.models.source import SourceSpan, SourceTrace


class TaskType(StrEnum):
    """Normalized task kinds for generators."""

    EMPTY = "empty"
    BASH = "bash"
    PYTHON = "python"
    BRANCH_PYTHON = "branch_python"
    SENSOR_FILE = "sensor_file"
    SENSOR_EXTERNAL = "sensor_external"
    TASK_GROUP = "task_group"
    UNKNOWN = "unknown"


class DependencyKind(StrEnum):
    """Edge semantics between tasks."""

    SUCCESS = "success"
    COMPLETION = "completion"
    CUSTOM = "custom"


class MappingStatus(StrEnum):
    """How completely an ESP construct mapped into IR/Airflow."""

    MAPPED = "mapped"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class EventKind(StrEnum):
    """ESP / workflow event categories."""

    FILE = "file"
    TIME = "time"
    TRIGGER = "trigger"
    APPLICATION = "application"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class EventMapping(StrEnum):
    """How an event was applied onto the workflow."""

    FILE_SENSOR = "file_sensor"
    SCHEDULE = "schedule"
    DEPENDENCY = "dependency"
    TRIGGER_RULE = "trigger_rule"
    EXTERNAL_SENSOR = "external_sensor"
    UNMAPPED = "unmapped"


class WorkflowMetadata(BaseModel):
    """Provenance and descriptive metadata for a workflow (≈ one DAG)."""

    model_config = ConfigDict(frozen=True)

    source_scheduler: str = "ESP"
    source_application: str
    source_file: str
    source_span: SourceSpan
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    conversion_version: str = "0.1.0"


class SensorSpec(BaseModel):
    """Sensor configuration attached to a task."""

    model_config = ConfigDict(frozen=True)

    sensor_type: str  # file | external_task | time
    filepath: str | None = None
    external_dag_id: str | None = None
    external_task_id: str | None = None
    poke_interval: int | None = None
    timeout: int | None = None
    mode: str | None = None


class BranchSpec(BaseModel):
    """Branching metadata for BranchPython-style tasks."""

    model_config = ConfigDict(frozen=True)

    callable_name: str | None = None
    branch_task_ids: list[str] = Field(default_factory=list)


class RetryPolicy(BaseModel):
    """Named or inline retry policy."""

    model_config = ConfigDict(frozen=True)

    policy_id: str
    max_attempts: int | None = None
    retry_delay: str | None = None
    trace: SourceTrace | None = None


class Notification(BaseModel):
    """Notification / alerting policy fragment."""

    model_config = ConfigDict(frozen=True)

    channel: str | None = None
    recipients: list[str] = Field(default_factory=list)
    on_event: str | None = None
    message: str | None = None
    trace: SourceTrace | None = None


class Variable(BaseModel):
    """Workflow or task-scoped variable."""

    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    scope: str | None = None
    trace: SourceTrace | None = None


class Resource(BaseModel):
    """Named resource / pool-like constraint."""

    model_config = ConfigDict(frozen=True)

    name: str
    quantity: int | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    trace: SourceTrace | None = None


class ScheduleSpec(BaseModel):
    """Schedule / timetable specification."""

    model_config = ConfigDict(frozen=True)

    raw_expression: str
    cron: str | None = None
    timetable: str | None = None
    calendar_ref: str | None = None
    start_date: str | None = None
    catchup: bool | None = False
    mapping_status: MappingStatus = MappingStatus.PARTIAL


class WorkflowEvent(BaseModel):
    """Event associated with a workflow after merge."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    kind: EventKind
    target_task_id: str | None = None
    payload: dict[str, str] = Field(default_factory=dict)
    mapped_as: EventMapping = EventMapping.UNMAPPED
    trace: SourceTrace


class Task(BaseModel):
    """One unit of work in the intermediate workflow."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    name: str
    task_type: TaskType = TaskType.UNKNOWN
    command: str | None = None
    pool: str | None = None
    priority_weight: int | None = None
    retry_policy_id: str | None = None
    trigger_rule: str | None = None
    sla: str | None = None
    sensor: SensorSpec | None = None
    branch: BranchSpec | None = None
    group_id: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    trace: SourceTrace
    unsupported_features: list[str] = Field(default_factory=list)


class Dependency(BaseModel):
    """Directed edge between tasks."""

    model_config = ConfigDict(frozen=True)

    upstream_task_id: str
    downstream_task_id: str
    kind: DependencyKind = DependencyKind.SUCCESS
    condition: str | None = None
    trace: SourceTrace | None = None


class Workflow(BaseModel):
    """Scheduler-independent workflow (aggregate root for one application/DAG)."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    metadata: WorkflowMetadata
    tasks: list[Task] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    schedule: ScheduleSpec | None = None
    variables: list[Variable] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    events: list[WorkflowEvent] = Field(default_factory=list)
    retry_policies: list[RetryPolicy] = Field(default_factory=list)
    notifications: list[Notification] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    def task_ids(self) -> list[str]:
        """Return task ids in declaration order."""
        return [task.task_id for task in self.tasks]
