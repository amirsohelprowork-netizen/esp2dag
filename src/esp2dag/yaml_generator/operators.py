"""Map Workflow tasks onto runnable DAG Factory operators (Airflow 3).

ESP job type → operator catalog (production migration):

Operating system / agents
- ``NT_JOB``              → WinRMOperator
- ``UNIX_JOB``/``AIX_JOB``/``LINUX_JOB`` → SSHOperator
- ``AS400_JOB``           → custom AS400Operator

Enterprise
- ``SAP_JOB``             → SapRfcOperator
- ``JOB`` (z/OS batch)    → MainframeSubmitJobOperator

Control / logical
- ``EXTERNAL``            → ExternalTaskSensor
- ``LINK`` / ``APPLEND`` / ``TASK`` → EmptyOperator
- ``DATA_OBJECT``         → PythonOperator
- ``AGENT_MONITOR``       → PythonOperator

Triggers
- ``FILE_TRIGGER``        → FileSensor
- ``DSTRIG``              → MainframeDatasetSensor
"""

from __future__ import annotations

import re
from typing import Any

from esp2dag.models.workflow import Task, TaskType
from esp2dag.utils import sanitize_task_id

# ---------------------------------------------------------------------------
# ESP Symbolic Variable → Airflow Jinja Template substitution
# ---------------------------------------------------------------------------

_ESP_VARIABLE_MAP: dict[str, str] = {
    "%ODATE": "{{ ds }}",
    "%OYEAR": "{{ logical_date.strftime('%Y') }}",
    "%OMONTH": "{{ logical_date.strftime('%m') }}",
    "%ODAY": "{{ logical_date.strftime('%d') }}",
    "%DATE": "{{ ds_nodash }}",
    "%TIME": "{{ ts_nodash }}",
    "%APPL": "{{ dag.dag_id }}",
    "%APPLICATION": "{{ dag.dag_id }}",
    "%JOB": "{{ task.task_id }}",
    "%JOBNAME": "{{ task.task_id }}",
    "%USER": "{{ params.get('esp_owner', 'maestro') }}",
    "%SCHEDDATE": "{{ ds }}",
    "%SCHEDTIME": "{{ logical_date.strftime('%H%M') }}",
    "%RUN_NUM": "{{ run_id }}",
}

# Build a single regex that matches any known ESP variable (longest first to
# handle %APPLICATION before %APPL, etc.).
_ESP_VAR_RE = re.compile(
    "|".join(
        re.escape(var) for var in sorted(_ESP_VARIABLE_MAP, key=len, reverse=True)
    ),
    re.IGNORECASE,
)


def substitute_esp_variables(text: str) -> str:
    """Replace ESP symbolic variables with Airflow Jinja template equivalents.

    Examples:
        >>> substitute_esp_variables('archive_data.sh %ODATE %APPL')
        'archive_data.sh {{ ds }} {{ dag.dag_id }}'
        >>> substitute_esp_variables('no variables here')
        'no variables here'
    """
    if not text or "%" not in text:
        return text

    def _replace(match: re.Match[str]) -> str:
        return _ESP_VARIABLE_MAP.get(match.group(0).upper(), match.group(0))

    return _ESP_VAR_RE.sub(_replace, text)


# ---------------------------------------------------------------------------
# Operator constants
# ---------------------------------------------------------------------------

AS400_OPERATOR = "custom_operators.as400.AS400Operator"
WINRM_OPERATOR = "airflow.providers.microsoft.winrm.operators.winrm.WinRMOperator"
SSH_OPERATOR = "airflow.providers.ssh.operators.ssh.SSHOperator"
SAP_OPERATOR = "airflow.providers.sap.operators.sap_rfc.SapRfcOperator"
MAINFRAME_OPERATOR = "custom_operators.mainframe.MainframeSubmitJobOperator"
MAINFRAME_DATASET_SENSOR = "custom_operators.mainframe.MainframeDatasetSensor"
EXTERNAL_SENSOR = "airflow.providers.standard.sensors.external_task.ExternalTaskSensor"
FILE_SENSOR = "airflow.providers.standard.sensors.filesystem.FileSensor"
EMPTY_OPERATOR = "airflow.providers.standard.operators.empty.EmptyOperator"
PYTHON_OPERATOR = "airflow.providers.standard.operators.python.PythonOperator"
BASH_OPERATOR = "airflow.providers.standard.operators.bash.BashOperator"

_SSH_JOB_TYPES = frozenset({"AIX_JOB", "UNIX_JOB", "LINUX_JOB"})
_EMPTY_JOB_TYPES = frozenset({"APPLEND", "LINK_JOB"})
_PYTHON_JOB_TYPES = frozenset({"DATA_OBJECT", "AGENT_MONITOR"})


def resolve_operator(task: Task) -> str:
    """Choose the operator import path for a task."""
    esp_type = (task.params.get("esp_job_type") or "").upper()

    if task.task_type == TaskType.SENSOR_EXTERNAL or _is_external(task):
        return EXTERNAL_SENSOR
    if esp_type in {"FILE_TRIGGER", "DSTRIG"} or task.task_type == TaskType.SENSOR_FILE:
        if esp_type == "DSTRIG" or task.params.get("dsname"):
            return MAINFRAME_DATASET_SENSOR
        return FILE_SENSOR
    if _is_link(task) or _is_task_marker(task) or esp_type in _EMPTY_JOB_TYPES:
        return EMPTY_OPERATOR
    if esp_type == "AS400_JOB":
        return AS400_OPERATOR
    if esp_type == "NT_JOB":
        return WINRM_OPERATOR
    if esp_type in _SSH_JOB_TYPES:
        return SSH_OPERATOR
    if esp_type == "SAP_JOB":
        return SAP_OPERATOR
    if esp_type in _PYTHON_JOB_TYPES or task.task_type == TaskType.PYTHON:
        return PYTHON_OPERATOR
    if esp_type == "JOB" and not _is_link(task) and not _is_external(task):
        return MAINFRAME_OPERATOR
    if task.task_type == TaskType.BASH and task.command:
        cmd = task.command
        if ":\\" in cmd or cmd.lower().endswith((".bat", ".cmd")):
            return WINRM_OPERATOR
        if cmd.startswith("/"):
            return SSH_OPERATOR
        return BASH_OPERATOR
    if task.task_type == TaskType.EMPTY and not task.command:
        return EMPTY_OPERATOR
    return EMPTY_OPERATOR


def build_task_fields(
    task: Task,
    *,
    yaml_task_id: str,
    retries: int | None = None,
    review_notes: list[str] | None = None,
) -> dict[str, Any]:
    """Build operator-specific YAML fields (excluding dependencies)."""
    operator = resolve_operator(task)
    fields: dict[str, Any] = {"operator": operator}
    agent = task.params.get("agent")
    jobq = task.params.get("jobq")
    args = task.params.get("args")

    if operator == EXTERNAL_SENSOR:
        appl = (
            (task.sensor.external_dag_id if task.sensor else None)
            or task.params.get("external_dag_id")
            or "unknown"
        )
        fields["external_dag_id"] = sanitize_task_id(appl).lower()
        # Converted DAGs use lower-case, sanitized task ids.  Retaining the
        # original ESP name here makes an all-converted estate fail to find
        # its target task (for example ``LIE.A`` vs ``lie_a``).
        fields["external_task_id"] = sanitize_task_id(
            (task.sensor.external_task_id if task.sensor else None) or task.name
        ).lower()
        fields["mode"] = "reschedule"
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == FILE_SENSOR:
        fields["filepath"] = (
            (task.sensor.filepath if task.sensor else None)
            or task.params.get("dstrig_file")
            or task.params.get("dsname")
            or task.params.get("filename")
            or ""
        )
        fields["poke_interval"] = 60
        fields["mode"] = "poke"
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == MAINFRAME_DATASET_SENSOR:
        fields["dsname"] = (
            task.params.get("dsname")
            or task.params.get("dstrig_file")
            or (task.sensor.filepath if task.sensor else None)
            or ""
        )
        fields["mode"] = "reschedule"
        fields["poke_interval"] = 60
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == EMPTY_OPERATOR:
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == AS400_OPERATOR:
        fields["conn_id"] = f"{agent}_AS400" if agent else "as400_default"
        fields["command"] = substitute_esp_variables(task.command or "")
        if jobq:
            fields["job_queue"] = jobq
        if not task.pool and agent:
            fields["pool"] = agent
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == WINRM_OPERATOR:
        # The provider exposes ``ssh_conn_id`` for its WinRM connection.  It
        # does not accept ``winrm_conn_id``.
        fields["ssh_conn_id"] = agent or "winrm_default"
        fields["command"] = substitute_esp_variables(task.command or "")
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == SSH_OPERATOR:
        fields["ssh_conn_id"] = agent or "ssh_default"
        fields["command"] = _ssh_command(task.command, args)
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == SAP_OPERATOR:
        fields["conn_id"] = agent or "sap_default"
        if task.params.get("abapname"):
            fields["abap_name"] = _strip_quotes(task.params["abapname"])
        if task.params.get("variant"):
            fields["variant"] = _strip_quotes(task.params["variant"])
        if task.params.get("sapjobname"):
            fields["sap_job_name"] = _strip_quotes(task.params["sapjobname"])
        if task.params.get("sapjobclass"):
            fields["sap_job_class"] = _strip_quotes(task.params["sapjobclass"])
        if task.params.get("stepuser"):
            fields["step_user"] = _strip_quotes(task.params["stepuser"])
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == MAINFRAME_OPERATOR:
        fields["job_name"] = task.name
        if task.params.get("jcl_library"):
            fields["jcl_library"] = _strip_quotes(task.params["jcl_library"])
        if task.params.get("ccchk"):
            fields["ccchk"] = task.params["ccchk"]
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == PYTHON_OPERATOR:
        esp_type = (task.params.get("esp_job_type") or "").upper()
        if esp_type == "AGENT_MONITOR":
            fields["python_callable"] = "esp_migration.agent_monitor.check"
        else:
            fields["python_callable"] = "esp_migration.data_object.execute"
        fields["op_kwargs"] = {"esp_job": task.name, "esp_type": esp_type or "DATA_OBJECT"}
        return _apply_common_fields(task, fields, retries, review_notes)

    if operator == BASH_OPERATOR:
        fields["bash_command"] = _ssh_command(task.command, args)
        return _apply_common_fields(task, fields, retries, review_notes)

    return _apply_common_fields(task, fields, retries, review_notes)


def _apply_common_fields(
    task: Task,
    fields: dict[str, Any],
    retries: int | None,
    review_notes: list[str] | None,
) -> dict[str, Any]:
    """Add BaseOperator fields consistently across every operator mapping."""
    notwith_pool = task.params.get("notwith_pool")
    if notwith_pool:
        fields["pool"] = notwith_pool
    elif task.pool and "pool" not in fields:
        fields["pool"] = task.pool
    if retries is not None:
        fields["retries"] = retries
    if task.priority_weight is not None:
        fields["priority_weight"] = task.priority_weight
    if task.trigger_rule:
        fields["trigger_rule"] = task.trigger_rule
    if review_notes:
        fields["doc_md"] = "### ESP migration review\n\n" + "\n".join(
            f"- {note}" for note in review_notes
        )
    return fields


def infer_owner(tasks: list[Task]) -> str:
    """Prefer Windows user leaf (e.g. bfusa\\maestro → maestro)."""
    for task in tasks:
        user = task.params.get("user")
        if user and "\\" in user:
            return user.split("\\")[-1]
        if user:
            return user
    return "maestro"


def _is_external(task: Task) -> bool:
    return bool(task.params.get("external")) or (
        task.sensor is not None and task.sensor.sensor_type == "external_task"
    )


def _is_link(task: Task) -> bool:
    return bool(task.params.get("link"))


def _is_task_marker(task: Task) -> bool:
    return bool(task.params.get("task"))


def _ssh_command(command: str | None, args: str | None) -> str:
    base = (command or "").strip()
    if args and args.strip():
        raw = f"{base} {args.strip()}".strip()
    else:
        raw = base
    return substitute_esp_variables(raw)


def _strip_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text
