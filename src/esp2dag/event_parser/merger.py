"""Merge ESP event catalog into Workflow IR — Phase 6b.

Enrichment only: produces new immutable ``Workflow`` copies. Never re-parses ESP
job bodies.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from esp2dag.yaml_generator.schedule_cron import esp_schedule_to_cron
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity
from esp2dag.models.events import EventCatalog, EventDefinition, EventJobBinding
from esp2dag.models.source import SourceTrace
from esp2dag.models.workflow import (
    EventKind,
    EventMapping,
    MappingStatus,
    ScheduleSpec,
    SensorSpec,
    Task,
    TaskType,
    Workflow,
    WorkflowEvent,
)
from esp2dag.utils import sanitize_task_id
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

STAGE = "event_merger"


class EventMergeResult(BaseModel):
    """Enriched workflows plus merge diagnostics."""

    model_config = ConfigDict(frozen=True)

    workflows: list[Workflow] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class EspEventMerger:
    """Associate events with workflows and map them onto IR constructs."""

    def merge(
        self,
        workflows: list[Workflow],
        catalog: EventCatalog,
    ) -> list[Workflow]:
        """Enrich workflows (protocol entrypoint)."""
        return self.merge_with_diagnostics(workflows, catalog).workflows

    def merge_with_diagnostics(
        self,
        workflows: list[Workflow],
        catalog: EventCatalog,
    ) -> EventMergeResult:
        """Merge catalog into workflows and return diagnostics."""
        logger.info(
            "Merging %d event(s) into %d workflow(s)",
            len(catalog.events),
            len(workflows),
        )
        by_appl = _index_bindings(catalog)
        events_by_name = catalog.events_by_name()
        workflow_names = {wf.name.upper(): wf for wf in workflows}

        diagnostics: list[Diagnostic] = []
        enriched: list[Workflow] = []
        matched_events: set[str] = set()

        for workflow in workflows:
            related = by_appl.get(workflow.name.upper(), [])
            # Also match event short-name == application name.
            for event in catalog.events:
                short = event.name.split(".")[-1].upper()
                if short == workflow.name.upper() and event.name not in {
                    b.event_name for b in related
                }:
                    related.append(
                        EventJobBinding(
                            event_name=event.name,
                            application=workflow.name,
                            attributes={"via": "event_id_suffix"},
                            span=event.span,
                        )
                    )

            if not related:
                enriched.append(workflow)
                continue

            wf, diags, used = _enrich_workflow(workflow, related, events_by_name)
            enriched.append(wf)
            diagnostics.extend(diags)
            matched_events.update(used)

        for event in catalog.events:
            if event.name in matched_events:
                continue
            # Orphan relative to the provided workflow set.
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.W_EVENT_ORPHAN,
                    severity=Severity.WARNING,
                    message=(
                        f"Event '{event.name}' did not match any compiled application "
                        f"in this run."
                    ),
                    stage=STAGE,
                    span=event.span,
                    hint=event.attributes.get("invoke_application"),
                )
            )

        _ = workflow_names
        logger.info(
            "Event merge complete: %d workflow(s), %d diagnostic(s)",
            len(enriched),
            len(diagnostics),
        )
        return EventMergeResult(workflows=enriched, diagnostics=diagnostics)


def _index_bindings(catalog: EventCatalog) -> dict[str, list[EventJobBinding]]:
    index: dict[str, list[EventJobBinding]] = defaultdict(list)
    for binding in catalog.bindings:
        if binding.application:
            index[binding.application.upper()].append(binding)
    return index


def _enrich_workflow(
    workflow: Workflow,
    bindings: list[EventJobBinding],
    events_by_name: dict[str, EventDefinition],
) -> tuple[Workflow, list[Diagnostic], set[str]]:
    diagnostics: list[Diagnostic] = []
    used: set[str] = set()
    new_events = list(workflow.events)
    new_tasks = list(workflow.tasks)
    tasks_by_name = {t.name.upper(): i for i, t in enumerate(new_tasks)}
    tasks_by_id = {t.task_id: i for i, t in enumerate(new_tasks)}
    schedule = workflow.schedule

    # Prefer scheduled event definitions for this application.
    schedule_candidates: list[EventDefinition] = []
    for binding in bindings:
        event = events_by_name.get(binding.event_name)
        if event is None:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.W_EVENT_UNMAPPED,
                    severity=Severity.WARNING,
                    message=f"Binding references unknown event '{binding.event_name}'.",
                    stage=STAGE,
                    application=workflow.name,
                )
            )
            continue
        used.add(event.name)

        mapped_as = EventMapping.UNMAPPED
        payload = dict(event.attributes)
        if binding.attributes.get("via") == "dstrig":
            mapped_as = EventMapping.FILE_SENSOR
            payload = {**payload, **binding.attributes}
            new_tasks, tasks_by_name, tasks_by_id, task_diag = _apply_file_trigger(
                workflow,
                new_tasks,
                tasks_by_name,
                tasks_by_id,
                binding,
            )
            diagnostics.extend(task_diag)
        elif event.kind == EventKind.TIME or event.attributes.get("schedule"):
            mapped_as = EventMapping.SCHEDULE
            schedule_candidates.append(event)
        elif event.kind == EventKind.APPLICATION or event.attributes.get("invoke"):
            mapped_as = EventMapping.DEPENDENCY
        else:
            mapped_as = EventMapping.UNMAPPED
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.W_EVENT_UNMAPPED,
                    severity=Severity.WARNING,
                    message=f"Event '{event.name}' could not be fully mapped.",
                    stage=STAGE,
                    application=workflow.name,
                    span=event.span,
                )
            )

        new_events.append(
            WorkflowEvent(
                event_id=event.name,
                kind=event.kind,
                target_task_id=_binding_task_id(binding, tasks_by_name, tasks_by_id),
                payload={k: str(v) for k, v in payload.items()},
                mapped_as=mapped_as,
                trace=binding.trace
                or SourceTrace(
                    source_file=event.span.file,
                    source_application=workflow.name,
                    source_job=binding.job,
                    source_line=event.span.start_line,
                    source_statement=event.span.text,
                ),
            )
        )

    if schedule_candidates:
        schedule = _merge_schedule(schedule, schedule_candidates)

    # Deduplicate workflow events by event_id preserving order.
    seen_ids: set[str] = set()
    deduped_events: list[WorkflowEvent] = []
    for event in new_events:
        key = f"{event.event_id}:{event.mapped_as}:{event.target_task_id}"
        if key in seen_ids:
            continue
        seen_ids.add(key)
        deduped_events.append(event)

    merged_diagnostics = list(workflow.diagnostics) + diagnostics
    updated = workflow.model_copy(
        update={
            "tasks": new_tasks,
            "events": deduped_events,
            "schedule": schedule,
            "diagnostics": merged_diagnostics,
        }
    )
    return updated, diagnostics, used


def _merge_schedule(
    current: ScheduleSpec | None,
    events: list[EventDefinition],
) -> ScheduleSpec:
    expressions: list[str] = []
    for event in events:
        raw = event.attributes.get("schedule")
        if raw:
            expressions.append(raw)
    joined = " | ".join(expressions) if expressions else (current.raw_expression if current else "")
    cron = esp_schedule_to_cron(joined)
    if cron is None and current is not None:
        cron = current.cron
    status = MappingStatus.MAPPED if cron else MappingStatus.PARTIAL
    return ScheduleSpec(
        raw_expression=joined or (current.raw_expression if current else "UNKNOWN"),
        cron=cron,
        calendar_ref=events[0].attributes.get("calendar"),
        catchup=False,
        mapping_status=status,
    )


def _apply_file_trigger(
    workflow: Workflow,
    tasks: list[Task],
    by_name: dict[str, int],
    by_id: dict[str, int],
    binding: EventJobBinding,
) -> tuple[list[Task], dict[str, int], dict[str, int], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    filepath = binding.attributes.get("filepath", "")
    job_name = binding.job or "FILE_TRIGGER"
    sensor = SensorSpec(sensor_type="file", filepath=filepath, mode="poke")

    if job_name.upper() in by_name:
        idx = by_name[job_name.upper()]
        old = tasks[idx]
        tasks[idx] = old.model_copy(
            update={
                "sensor": sensor,
                "task_type": TaskType.SENSOR_FILE
                if old.task_type in {TaskType.EMPTY, TaskType.UNKNOWN}
                else old.task_type,
                "unsupported_features": list(old.unsupported_features) + ["dstrig"],
                "params": {**old.params, "dstrig_file": filepath},
            }
        )
        return tasks, by_name, by_id, diagnostics

    # Create a new sensor task when job is not in the application body.
    task_id = sanitize_task_id(job_name)
    if task_id in by_id:
        task_id = f"{task_id}_sensor"
    new_task = Task(
        task_id=task_id,
        name=job_name,
        task_type=TaskType.SENSOR_FILE,
        sensor=sensor,
        params={"dstrig_file": filepath, "esp_job_type": "DSTRIG"},
        trace=binding.trace
        or SourceTrace(
            source_file=workflow.metadata.source_file,
            source_application=workflow.name,
            source_job=job_name,
            source_line=1,
            source_statement=f"DSTRIG {filepath}",
        ),
        unsupported_features=["dstrig_synthetic_task"],
    )
    tasks.append(new_task)
    by_name[job_name.upper()] = len(tasks) - 1
    by_id[task_id] = len(tasks) - 1
    diagnostics.append(
        Diagnostic(
            code=DiagnosticCode.W_EVENT_UNMAPPED,
            severity=Severity.WARNING,
            message=(
                f"DSTRIG job '{job_name}' not found in application '{workflow.name}'; "
                f"created sensor task '{task_id}'."
            ),
            stage=STAGE,
            application=workflow.name,
            job=job_name,
        )
    )
    return tasks, by_name, by_id, diagnostics


def _binding_task_id(
    binding: EventJobBinding,
    by_name: dict[str, int],
    by_id: dict[str, int],
) -> str | None:
    _ = by_id
    if binding.job and binding.job.upper() in by_name:
        # Caller may have updated tasks; id resolve deferred — use sanitized name.
        return sanitize_task_id(binding.job)
    return None
