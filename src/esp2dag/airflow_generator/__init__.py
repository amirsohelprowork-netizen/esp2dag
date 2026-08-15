"""Native Apache Airflow 3 DAG generator.

The generator deliberately consumes the scheduler-neutral :class:`Workflow` IR,
just like the DAG Factory backend.  It emits ordinary Python modules rather
than importing or parsing ESP at DAG-discovery time.
"""

from __future__ import annotations

import re
from datetime import datetime

from esp2dag.compiler.workflow.notwith import assign_notwith_pools
from esp2dag.models.workflow import MappingStatus, Notification, Task, Workflow
from esp2dag.utils import sanitize_task_id
from esp2dag.yaml_generator.operators import (
    AS400_OPERATOR,
    BASH_OPERATOR,
    EMPTY_OPERATOR,
    EXTERNAL_SENSOR,
    FILE_SENSOR,
    MAINFRAME_DATASET_SENSOR,
    MAINFRAME_OPERATOR,
    PYTHON_OPERATOR,
    SAP_OPERATOR,
    SSH_OPERATOR,
    WINRM_OPERATOR,
    build_task_fields,
    infer_owner,
)
from esp2dag.yaml_generator.schedule_cron import esp_schedule_to_cron


DEFAULT_START_DATE = "2024-01-01"

_OPERATOR_IMPORTS = {
    AS400_OPERATOR: "from custom_operators.as400 import AS400Operator",
    BASH_OPERATOR: "from airflow.providers.standard.operators.bash import BashOperator",
    EMPTY_OPERATOR: "from airflow.providers.standard.operators.empty import EmptyOperator",
    EXTERNAL_SENSOR: (
        "from airflow.providers.standard.sensors.external_task import ExternalTaskSensor"
    ),
    FILE_SENSOR: "from airflow.providers.standard.sensors.filesystem import FileSensor",
    MAINFRAME_DATASET_SENSOR: (
        "from custom_operators.mainframe import MainframeDatasetSensor"
    ),
    MAINFRAME_OPERATOR: (
        "from custom_operators.mainframe import MainframeSubmitJobOperator"
    ),
    PYTHON_OPERATOR: "from airflow.providers.standard.operators.python import PythonOperator",
    SAP_OPERATOR: "from airflow.providers.sap.operators.sap_rfc import SapRfcOperator",
    SSH_OPERATOR: "from airflow.providers.ssh.operators.ssh import SSHOperator",
    WINRM_OPERATOR: "from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator",
}

_OPERATOR_CLASSES = {
    AS400_OPERATOR: "AS400Operator",
    BASH_OPERATOR: "BashOperator",
    EMPTY_OPERATOR: "EmptyOperator",
    EXTERNAL_SENSOR: "ExternalTaskSensor",
    FILE_SENSOR: "FileSensor",
    MAINFRAME_DATASET_SENSOR: "MainframeDatasetSensor",
    MAINFRAME_OPERATOR: "MainframeSubmitJobOperator",
    PYTHON_OPERATOR: "PythonOperator",
    SAP_OPERATOR: "SapRfcOperator",
    SSH_OPERATOR: "SSHOperator",
    WINRM_OPERATOR: "WinRMOperator",
}


class AirflowDagGenerator:
    """Emit deterministic, importable Airflow 3 Python modules from Workflow IR."""

    def generate(self, workflow: Workflow) -> str:
        """Generate a Python DAG module string."""
        if not any(task.params.get("notwith_pool") for task in workflow.tasks):
            workflow = assign_notwith_pools([workflow])[0]

        task_rows = [_task_row(workflow, task) for task in workflow.tasks]
        imports = _imports_for(task_rows)
        lines = [
            '"""Generated from CA ESP application ' + repr(workflow.name) + '."""',
            "",
            "from __future__ import annotations",
            "",
            "from datetime import datetime, timedelta, timezone",
            "",
            "from airflow.sdk import DAG",
            *imports,
            "",
        ]
        if any(row["operator"] == PYTHON_OPERATOR for row in task_rows):
            lines.extend(_manual_task_function())

        # Emit NOTIFY callback functions.
        callback_lines = _render_notify_callbacks(workflow)
        if callback_lines:
            lines.extend(callback_lines)

        lines.extend(_dag_header(workflow))
        lines.append("    tasks = {}")
        for row in task_rows:
            lines.extend(_render_task(row))
        if workflow.dependencies:
            lines.append("")
            lines.extend(_render_dependencies(workflow))
        lines.append("")
        return "\n".join(lines)


def _imports_for(rows: list[dict[str, object]]) -> list[str]:
    """Return sorted imports for exactly the operators used by this DAG."""
    operator_paths = {str(row["operator"]) for row in rows}
    return sorted(_OPERATOR_IMPORTS[path] for path in operator_paths)


def _manual_task_function() -> list[str]:
    """Emit a safe failure for ESP controls that need a site-specific adapter."""
    return [
        "def _esp_manual_task(*, esp_job: str, esp_type: str, **_: object) -> None:",
        '    """Fail loudly instead of pretending an ESP control task was migrated."""',
        "    raise RuntimeError(",
        '        f"ESP {esp_type} task {esp_job!r} requires a site-specific Airflow adapter."',
        "    )",
        "",
    ]


def _dag_header(workflow: Workflow) -> list[str]:
    start_date = _start_date(workflow)
    tags = list(dict.fromkeys(["esp", *workflow.metadata.tags]))
    default_args = _build_default_args(workflow)
    return [
        "with DAG(",
        f"    dag_id={workflow.id!r},",
        f"    description={_description(workflow)!r},",
        f"    schedule={_schedule_value(workflow)!r},",
        (
            "    start_date=datetime("
            f"{start_date.year}, {start_date.month}, {start_date.day}, tzinfo=timezone.utc),"
        ),
        "    catchup=False,",
        f"    default_args={default_args!r},",
        f"    tags={tags!r},",
        ") as dag:",
    ]


def _task_row(workflow: Workflow, task: Task) -> dict[str, object]:
    """Build the shared operator mapping plus native-Python-only provenance."""
    task_id = sanitize_task_id(task.task_id).lower()
    fields = build_task_fields(
        task,
        yaml_task_id=task_id,
        retries=_retries_for(workflow, task),
        review_notes=_review_notes(workflow, task),
    )
    source_note = (
        f"ESP source: {task.trace.source_file}:{task.trace.source_line} "
        f"(application {task.trace.source_application}, job {task.name})"
    )
    doc_md = fields.get("doc_md")
    fields["doc_md"] = f"{doc_md}\n\n{source_note}" if doc_md else source_note
    fields["params"] = {
        "esp_source_application": task.trace.source_application,
        "esp_source_job": task.name,
        "esp_source_line": task.trace.source_line,
    }
    return {"task_id": task_id, "operator": fields.pop("operator"), "fields": fields}


def _render_task(row: dict[str, object]) -> list[str]:
    task_id = str(row["task_id"])
    operator = str(row["operator"])
    fields = dict(row["fields"])
    class_name = _OPERATOR_CLASSES[operator]
    if operator == PYTHON_OPERATOR:
        # YAML represents callables as strings.  Native Python DAGs need an
        # actual callable, and this intentionally fails until the migration
        # is completed rather than marking an unmigrated task successful.
        fields["python_callable"] = "_esp_manual_task"

    lines = [
        f"    tasks[{task_id!r}] = {class_name}(",
        f"        task_id={task_id!r},",
    ]
    for key, value in fields.items():
        rendered = (
            value
            if key == "python_callable" and value == "_esp_manual_task"
            else repr(value)
        )
        lines.append(f"        {key}={rendered},")
    lines.append("    )")
    return lines


def _render_dependencies(workflow: Workflow) -> list[str]:
    known = {sanitize_task_id(task.task_id).lower() for task in workflow.tasks}
    edges: list[tuple[str, str]] = []
    for dependency in workflow.dependencies:
        upstream = sanitize_task_id(dependency.upstream_task_id).lower()
        downstream = sanitize_task_id(dependency.downstream_task_id).lower()
        if upstream in known and downstream in known:
            edges.append((upstream, downstream))
    return [
        f"    tasks[{upstream!r}] >> tasks[{downstream!r}]"
        for upstream, downstream in sorted(set(edges))
    ]


def _schedule_value(workflow: Workflow) -> str | None:
    if workflow.schedule is None or workflow.schedule.mapping_status != MappingStatus.MAPPED:
        return None
    return esp_schedule_to_cron(workflow.schedule.raw_expression) or workflow.schedule.cron


def _start_date(workflow: Workflow) -> datetime:
    raw = workflow.schedule.start_date if workflow.schedule else None
    text = raw or DEFAULT_START_DATE
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        return datetime.fromisoformat(DEFAULT_START_DATE)


def _description(workflow: Workflow) -> str:
    base = workflow.metadata.description or f"ESP application {workflow.name}"
    if workflow.schedule and workflow.schedule.mapping_status != MappingStatus.MAPPED:
        return f"{base}. Schedule requires migration review: {workflow.schedule.raw_expression}"
    return base


def _retries_for(workflow: Workflow, task: Task) -> int | None:
    if task.retry_policy_id is None:
        return None
    for policy in workflow.retry_policies:
        if policy.policy_id == task.retry_policy_id:
            return policy.max_attempts
    return None


def _review_notes(workflow: Workflow, task: Task) -> list[str]:
    notes = list(task.unsupported_features)
    for dependency in workflow.dependencies:
        if dependency.downstream_task_id != task.task_id:
            continue
        if dependency.condition:
            notes.append(
                f"ESP dependency condition from `{dependency.upstream_task_id}`: "
                f"`{dependency.condition}`. Generated dependency is success-based; review it."
            )
        elif dependency.kind.value != "success":
            notes.append(
                f"ESP dependency from `{dependency.upstream_task_id}` has kind "
                f"`{dependency.kind.value}`; review the generated success-based dependency."
            )
    return notes
