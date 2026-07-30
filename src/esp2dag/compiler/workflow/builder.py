"""AST → Workflow IR builder — Phase 5.

Lowers an ``ApplicationNode`` into a scheduler-independent ``Workflow``.
Nothing downstream should need ESP AST/token types.
"""

from __future__ import annotations

import logging

from esp2dag.compiler.ast.nodes import (
    ApplicationNode,
    DependencyNode,
    JobNode,
    NotificationNode,
)
from esp2dag.compiler.workflow.job_mapping import map_task_type, meta_value
from esp2dag.compiler.workflow.task_ids import TaskIdAllocator
from esp2dag.models.diagnostics import Diagnostic
from esp2dag.models.source import SourceTrace
from esp2dag.models.workflow import (
    Dependency,
    DependencyKind,
    MappingStatus,
    Notification,
    Resource,
    RetryPolicy,
    ScheduleSpec,
    Task,
    Variable,
    Workflow,
    WorkflowEvent,
    WorkflowMetadata,
    EventKind,
    EventMapping,
)
from esp2dag.utils import sanitize_task_id

logger = logging.getLogger(__name__)


class EspWorkflowBuilder:
    """Build a ``Workflow`` IR from a semantically analyzed application AST."""

    def build(
        self,
        ast: ApplicationNode,
        diagnostics: list[Diagnostic],
    ) -> Workflow:
        """Lower AST into scheduler-independent Workflow IR."""
        logger.info("Building workflow IR for application %s", ast.name)
        allocator = TaskIdAllocator()

        # Pre-allocate ids in declaration order for stable dependency resolution.
        for job in ast.jobs:
            allocator.allocate(job.name)

        tasks = [self._build_task(ast, job, allocator) for job in ast.jobs]
        dependencies = self._build_dependencies(ast, allocator)
        schedule = self._build_schedule(ast)
        variables = self._build_variables(ast)
        resources = self._build_resources(ast)
        notifications = self._build_notifications(ast)
        retry_policies = self._build_retry_policies(ast, allocator)
        events = self._build_event_refs(ast, allocator)
        tags = sorted({m.value for m in ast.metadata if m.key == "tag" and m.value})

        workflow = Workflow(
            id=sanitize_task_id(ast.name).lower(),
            name=ast.name,
            metadata=WorkflowMetadata(
                source_scheduler="ESP",
                source_application=ast.name,
                source_file=ast.span.file,
                source_span=ast.span,
                description=self._description(ast),
                tags=tags,
            ),
            tasks=tasks,
            dependencies=dependencies,
            schedule=schedule,
            variables=variables,
            resources=resources,
            events=events,
            retry_policies=retry_policies,
            notifications=notifications,
            diagnostics=list(diagnostics),
        )
        logger.info(
            "Workflow %s: %d task(s), %d edge(s)",
            workflow.id,
            len(workflow.tasks),
            len(workflow.dependencies),
        )
        return workflow

    def _build_task(
        self,
        ast: ApplicationNode,
        job: JobNode,
        allocator: TaskIdAllocator,
    ) -> Task:
        task_id = allocator.allocate(job.name)
        task_type, sensor, unsupported = map_task_type(job)
        unsupported = list(unsupported)
        unsupported.extend(f"unsupported:{u.keyword}" for u in job.unsupported)

        params: dict[str, str] = {}
        agent = meta_value(job, "agent")
        if agent:
            params["agent"] = agent
        user = meta_value(job, "user")
        if user:
            params["user"] = user
        jobq = meta_value(job, "jobq")
        if jobq:
            params["jobq"] = jobq
        args = meta_value(job, "args")
        if args:
            params["args"] = args
        if job.job_type:
            params["esp_job_type"] = job.job_type
        else:
            params["esp_job_type"] = "JOB"
        if any(m.key == "link" for m in job.metadata):
            params["link"] = "true"
        if any(m.key == "external" for m in job.metadata):
            params["external"] = "true"
        if any(m.key == "task" for m in job.metadata):
            params["task"] = "true"
        for meta in job.metadata:
            if meta.key in {
                "agent",
                "user",
                "jobq",
                "args",
                "link",
                "external",
                "task",
                "process",
                "header_attr",
                "conditional",
            }:
                continue
            if meta.key == "notwith" and meta.value:
                peers = [
                    p.strip()
                    for p in params.get("notwith_peers", "").split(",")
                    if p.strip()
                ]
                if meta.value.strip() not in peers:
                    peers.append(meta.value.strip())
                params["notwith_peers"] = ",".join(peers)
                continue
            if meta.value and meta.key not in params:
                params[meta.key] = meta.value

        pool = None
        if job.resources:
            pool = job.resources[0].name

        retry_policy_id = None
        if job.retry is not None:
            retry_policy_id = f"retry_{task_id}"

        command = job.command.text if job.command else None
        trace = SourceTrace(
            source_file=job.span.file,
            source_application=ast.name,
            source_job=job.name,
            source_line=job.span.start_line,
            source_column=job.span.start_column,
            source_statement=job.span.text,
        )
        return Task(
            task_id=task_id,
            name=job.name,
            task_type=task_type,
            command=command,
            pool=pool,
            retry_policy_id=retry_policy_id,
            sensor=sensor,
            params=params,
            trace=trace,
            unsupported_features=unsupported,
        )

    def _build_dependencies(
        self,
        ast: ApplicationNode,
        allocator: TaskIdAllocator,
    ) -> list[Dependency]:
        edges: list[Dependency] = []
        seen: set[tuple[str, str, str]] = set()

        for job in ast.jobs:
            upstream_id = allocator.allocate(job.name)
            for dep in job.dependencies:
                target_name = dep.predecessor
                downstream_id = allocator.resolve(target_name)
                kind = (dep.dependency_type or "AFTER").upper()

                if kind == "RELEASE":
                    # job releases target ⇒ upstream=job, downstream=target
                    if downstream_id is None:
                        # Keep dangling edge via sanitized id for later event merge.
                        downstream_id = sanitize_task_id(target_name.split("(", 1)[0])
                    edge = self._edge(
                        upstream_id,
                        downstream_id,
                        dep,
                        ast.name,
                        job.name,
                    )
                else:
                    # AFTER-style: predecessor → job
                    pred_id = allocator.resolve(target_name)
                    if pred_id is None:
                        pred_id = sanitize_task_id(target_name.split("(", 1)[0])
                    edge = self._edge(
                        pred_id,
                        upstream_id,
                        dep,
                        ast.name,
                        job.name,
                    )

                key = (edge.upstream_task_id, edge.downstream_task_id, edge.kind.value)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(edge)

        # Deterministic order: upstream then downstream.
        edges.sort(key=lambda e: (e.upstream_task_id, e.downstream_task_id, e.kind.value))
        return edges

    def _edge(
        self,
        upstream: str,
        downstream: str,
        dep: DependencyNode,
        application: str,
        job_name: str,
    ) -> Dependency:
        kind = DependencyKind.SUCCESS
        if (dep.dependency_type or "").upper() not in {"", "RELEASE", "AFTER", "SUCCESS"}:
            kind = DependencyKind.CUSTOM
        trace = None
        if dep.span is not None:
            trace = SourceTrace(
                source_file=dep.span.file,
                source_application=application,
                source_job=job_name,
                source_line=dep.span.start_line,
                source_column=dep.span.start_column,
                source_statement=dep.span.text,
            )
        return Dependency(
            upstream_task_id=upstream,
            downstream_task_id=downstream,
            kind=kind,
            condition=dep.condition.expression if dep.condition else None,
            trace=trace,
        )

    def _build_schedule(self, ast: ApplicationNode) -> ScheduleSpec | None:
        # Prefer first concrete RUN expression among jobs.
        for job in ast.jobs:
            if job.schedule and job.schedule.expression.strip():
                expr = job.schedule.expression.strip()
                status = MappingStatus.PARTIAL
                cron = None
                if expr.upper() == "DAILY":
                    cron = "0 0 * * *"
                    status = MappingStatus.MAPPED
                return ScheduleSpec(
                    raw_expression=expr,
                    cron=cron,
                    catchup=False,
                    mapping_status=status,
                )
        for schedule in ast.schedules:
            if schedule.expression.strip():
                return ScheduleSpec(
                    raw_expression=schedule.expression.strip(),
                    catchup=False,
                    mapping_status=MappingStatus.PARTIAL,
                )
        return None

    def _build_variables(self, ast: ApplicationNode) -> list[Variable]:
        variables: list[Variable] = [
            Variable(
                name=v.name,
                value=v.value,
                scope=v.scope or "appl",
                trace=SourceTrace.from_span(
                    application=ast.name, job=None, span=v.span
                ),
            )
            for v in ast.variables
        ]
        for job in ast.jobs:
            for var in job.variables:
                variables.append(
                    Variable(
                        name=var.name,
                        value=var.value,
                        scope=var.scope or "job",
                        trace=SourceTrace.from_span(
                            application=ast.name, job=job.name, span=var.span
                        ),
                    )
                )
        return variables

    def _build_resources(self, ast: ApplicationNode) -> list[Resource]:
        resources = [
            Resource(
                name=r.name,
                quantity=r.quantity,
                attributes=dict(r.attributes),
                trace=SourceTrace.from_span(application=ast.name, job=None, span=r.span),
            )
            for r in ast.resources
        ]
        # Also collect unique job-scoped resource refs as resources if not declared.
        seen = {r.name.upper() for r in resources}
        for job in ast.jobs:
            for ref in job.resources:
                if ref.name.upper() in seen:
                    continue
                seen.add(ref.name.upper())
                resources.append(
                    Resource(
                        name=ref.name,
                        quantity=ref.quantity,
                        attributes=dict(ref.attributes),
                        trace=SourceTrace.from_span(
                            application=ast.name, job=job.name, span=ref.span
                        ),
                    )
                )
        return resources

    def _build_notifications(self, ast: ApplicationNode) -> list[Notification]:
        notes = [self._map_notification(n, ast.name, None) for n in ast.notifications]
        for job in ast.jobs:
            notes.extend(
                self._map_notification(n, ast.name, job.name) for n in job.notifications
            )
        return notes

    def _map_notification(
        self,
        node: NotificationNode,
        application: str,
        job: str | None,
    ) -> Notification:
        return Notification(
            channel=node.channel,
            recipients=list(node.recipients),
            on_event=node.on_event,
            message=node.message,
            trace=SourceTrace.from_span(application=application, job=job, span=node.span),
        )

    def _build_retry_policies(
        self,
        ast: ApplicationNode,
        allocator: TaskIdAllocator,
    ) -> list[RetryPolicy]:
        policies: list[RetryPolicy] = []
        for job in ast.jobs:
            if job.retry is None:
                continue
            task_id = allocator.allocate(job.name)
            policies.append(
                RetryPolicy(
                    policy_id=f"retry_{task_id}",
                    max_attempts=job.retry.max_attempts,
                    retry_delay=job.retry.interval,
                    trace=SourceTrace.from_span(
                        application=ast.name, job=job.name, span=job.retry.span
                    ),
                )
            )
        return policies

    def _build_event_refs(
        self,
        ast: ApplicationNode,
        allocator: TaskIdAllocator,
    ) -> list[WorkflowEvent]:
        events: list[WorkflowEvent] = []
        for job in ast.jobs:
            task_id = allocator.allocate(job.name)
            for ref in job.event_refs:
                events.append(
                    WorkflowEvent(
                        event_id=ref.event_name,
                        kind=EventKind.APPLICATION,
                        target_task_id=task_id,
                        payload={"applid": ref.event_name},
                        mapped_as=EventMapping.EXTERNAL_SENSOR,
                        trace=SourceTrace.from_span(
                            application=ast.name, job=job.name, span=ref.span
                        ),
                    )
                )
        return events

    def _description(self, ast: ApplicationNode) -> str | None:
        invoke = next((m.value for m in ast.metadata if m.key == "invoke"), None)
        if invoke:
            return f"ESP application {ast.name} (INVOKE {invoke})"
        return f"ESP application {ast.name}"
