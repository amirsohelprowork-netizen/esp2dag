"""Deterministic DAG Factory YAML emitter — Phase 7.

Default profile matches the production migration target:

- dict tasks keyed by lowercase task_id
- ``dependencies`` (not depends_on)
- runnable operators: AS400Operator / WinRMOperator / SSHOperator / sensors
- connection ids derived from ESP AGENT
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from esp2dag.models.workflow import MappingStatus, Task, Workflow
from esp2dag.compiler.workflow.notwith import assign_notwith_pools
from esp2dag.yaml_generator.operators import build_task_fields, infer_owner
from esp2dag.yaml_generator.schedule_cron import esp_schedule_to_cron

logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "2024-01-01"


class DagFactoryYamlGenerator:
    """Emit deterministic DAG Factory-compatible YAML from Workflow IR."""

    def __init__(
        self,
        *,
        profile: str = "default",
        include_metadata: bool = False,
    ) -> None:
        self._profile = profile.lower().strip() or "default"
        self._include_metadata = include_metadata

    def generate(self, workflow: Workflow) -> str:
        """Generate YAML text for one workflow."""
        logger.info(
            "Generating DAG Factory YAML for %s (profile=%s)",
            workflow.id,
            self._profile,
        )
        # Local assign when pools were not already applied by the batch pipeline.
        if not any(t.params.get("notwith_pool") for t in workflow.tasks):
            workflow = assign_notwith_pools([workflow])[0]
        if self._profile in {"astronomer", "list"}:
            document = self._build_list_document(workflow)
        else:
            document = self._build_default_document(workflow)
        return dump_canonical_yaml(document)

    def _build_default_document(self, workflow: Workflow) -> dict[str, Any]:
        id_map = {t.task_id: t.task_id.lower() for t in workflow.tasks}
        upstream = _upstream_map(workflow, id_map)

        tasks: dict[str, Any] = {}
        for task in workflow.tasks:
            yaml_id = id_map[task.task_id]
            body = build_task_fields(
                task,
                yaml_task_id=yaml_id,
                retries=_retries_for(workflow, task),
                review_notes=_review_notes(workflow, task),
            )
            deps = upstream.get(yaml_id, [])
            if deps:
                body["dependencies"] = deps
            if self._include_metadata:
                body["metadata"] = _metadata(task)
            tasks[yaml_id] = body

        # Preserve task declaration order (not alphabetical) for readability.
        ordered_tasks = {
            id_map[t.task_id]: tasks[id_map[t.task_id]] for t in workflow.tasks
        }

        dag_body: dict[str, Any] = {
            "catchup": False,
            "default_args": {
                "owner": infer_owner(workflow.tasks),
                "start_date": (
                    workflow.schedule.start_date
                    if workflow.schedule and workflow.schedule.start_date
                    else DEFAULT_START_DATE
                ),
            },
            "description": _description(workflow),
            "schedule": _schedule_value(workflow),
            "tasks": ordered_tasks,
        }
        return {workflow.id: dag_body}

    def _build_list_document(self, workflow: Workflow) -> dict[str, Any]:
        id_map = {t.task_id: t.task_id.lower() for t in workflow.tasks}
        upstream = _upstream_map(workflow, id_map)
        tasks: list[dict[str, Any]] = []
        for task in workflow.tasks:
            yaml_id = id_map[task.task_id]
            item = {
                "task_id": yaml_id,
                **build_task_fields(
                    task,
                    yaml_task_id=yaml_id,
                    retries=_retries_for(workflow, task),
                    review_notes=_review_notes(workflow, task),
                ),
            }
            deps = upstream.get(yaml_id, [])
            if deps:
                item["dependencies"] = deps
            tasks.append(item)
        return {
            workflow.id: {
                "catchup": False,
                "default_args": {
                    "owner": infer_owner(workflow.tasks),
                    "start_date": DEFAULT_START_DATE,
                },
                "description": _description(workflow),
                "schedule": _schedule_value(workflow),
                "tasks": tasks,
            }
        }


def _upstream_map(workflow: Workflow, id_map: dict[str, str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {id_map[t.task_id]: [] for t in workflow.tasks}
    known = set(mapping)
    for dep in workflow.dependencies:
        up = id_map.get(dep.upstream_task_id)
        down = id_map.get(dep.downstream_task_id)
        if up in known and down in known:
            mapping[down].append(up)
    for key, ups in mapping.items():
        mapping[key] = sorted(set(ups))
    return mapping


def _schedule_value(workflow: Workflow) -> str | None:
    if workflow.schedule is None:
        return None
    # Never emit an ESP expression as though it were an Airflow cron.  An
    # unmapped calendar/schedule must remain unscheduled until reviewed.
    if workflow.schedule.mapping_status != MappingStatus.MAPPED:
        return None
    converted = esp_schedule_to_cron(workflow.schedule.raw_expression)
    return converted or workflow.schedule.cron


def _description(workflow: Workflow) -> str:
    tags = [t for t in workflow.metadata.tags if t.upper() not in {"ESP", "MIGRATED"}]
    if tags:
        return f"{workflow.name} ({', '.join(tags)})"
    return f"{workflow.name} application"


def _metadata(task: Task) -> dict[str, Any]:
    return {
        "source_application": task.trace.source_application,
        "source_file": task.trace.source_file,
        "source_job": task.trace.source_job,
        "source_line": task.trace.source_line,
        "source_scheduler": "ESP",
    }


def _retries_for(workflow: Workflow, task: Task) -> int | None:
    if task.retry_policy_id is None:
        return None
    for policy in workflow.retry_policies:
        if policy.policy_id == task.retry_policy_id:
            return policy.max_attempts
    return None


def _review_notes(workflow: Workflow, task: Task) -> list[str]:
    """Return valid-Airflow documentation for semantics needing a human."""
    notes = list(task.unsupported_features)
    for dep in workflow.dependencies:
        if dep.downstream_task_id != task.task_id:
            continue
        if dep.condition:
            notes.append(
                f"ESP dependency condition from `{dep.upstream_task_id}`: "
                f"`{dep.condition}`. "
                "The generated dependency is success-based; review the trigger rule."
            )
        elif dep.kind != "success":
            notes.append(
                f"ESP dependency from `{dep.upstream_task_id}` has kind `{dep.kind}`; "
                "review the generated success-based dependency."
            )
    return notes


def dump_canonical_yaml(document: dict[str, Any]) -> str:
    """Dump YAML with stable formatting.

    Task key order is preserved (declaration order). Nested mappings use
    sorted keys for determinism.
    """

    class _Dumper(yaml.SafeDumper):
        pass

    def _str_representer(dumper: yaml.SafeDumper, data: str) -> Any:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    def _dict_representer(dumper: yaml.SafeDumper, data: dict[str, Any]) -> Any:
        # Preserve insertion order for top-level task dicts; sort only nested
        # operator field dicts by dumping as-is (Python 3.7+ order).
        return dumper.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=False)

    _Dumper.add_representer(str, _str_representer)
    _Dumper.add_representer(dict, _dict_representer)

    # Sort only dag-level keys, keep tasks insertion order by rebuilding.
    dag_id, body = next(iter(document.items()))
    tasks = body.get("tasks")
    ordered_body = {
        "description": body.get("description"),
        "schedule": body.get("schedule"),
        "catchup": body.get("catchup"),
        "default_args": body.get("default_args"),
        "tasks": tasks,
    }
    # Drop Nones
    ordered_body = {k: v for k, v in ordered_body.items() if v is not None}

    text = yaml.dump(
        {dag_id: ordered_body},
        Dumper=_Dumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    if not text.endswith("\n"):
        text += "\n"
    return text
