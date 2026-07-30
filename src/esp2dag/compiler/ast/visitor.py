"""AST visitor protocol / base class."""

from __future__ import annotations

from typing import Generic, TypeVar

from esp2dag.compiler.ast.nodes import (
    ApplicationNode,
    CalendarNode,
    CommandNode,
    ConditionNode,
    DependencyNode,
    EventReferenceNode,
    JobNode,
    MetadataNode,
    NotificationNode,
    ResourceNode,
    ResourceRefNode,
    RetryNode,
    ScheduleNode,
    UnsupportedStatementNode,
    VariableNode,
)

T = TypeVar("T")


class AstVisitor(Generic[T]):
    """Visitor base for AST traversal.

    Concrete analyzers/builders override only the methods they need.
    Default implementations recurse into children where applicable.
    """

    def visit_application(self, node: ApplicationNode) -> T:
        for job in node.jobs:
            job.accept(self)
        for calendar in node.calendars:
            calendar.accept(self)
        for schedule in node.schedules:
            schedule.accept(self)
        for resource in node.resources:
            resource.accept(self)
        for variable in node.variables:
            variable.accept(self)
        for notification in node.notifications:
            notification.accept(self)
        for meta in node.metadata:
            meta.accept(self)
        for unsupported in node.unsupported:
            unsupported.accept(self)
        return self._default(node)

    def visit_job(self, node: JobNode) -> T:
        if node.command is not None:
            node.command.accept(self)
        for dep in node.dependencies:
            dep.accept(self)
        for condition in node.conditions:
            condition.accept(self)
        for resource in node.resources:
            resource.accept(self)
        if node.retry is not None:
            node.retry.accept(self)
        for notification in node.notifications:
            notification.accept(self)
        for event_ref in node.event_refs:
            event_ref.accept(self)
        if node.schedule is not None:
            node.schedule.accept(self)
        for variable in node.variables:
            variable.accept(self)
        for meta in node.metadata:
            meta.accept(self)
        for unsupported in node.unsupported:
            unsupported.accept(self)
        return self._default(node)

    def visit_dependency(self, node: DependencyNode) -> T:
        if node.condition is not None:
            node.condition.accept(self)
        return self._default(node)

    def visit_condition(self, node: ConditionNode) -> T:
        return self._default(node)

    def visit_calendar(self, node: CalendarNode) -> T:
        return self._default(node)

    def visit_schedule(self, node: ScheduleNode) -> T:
        return self._default(node)

    def visit_resource(self, node: ResourceNode) -> T:
        return self._default(node)

    def visit_resource_ref(self, node: ResourceRefNode) -> T:
        return self._default(node)

    def visit_variable(self, node: VariableNode) -> T:
        return self._default(node)

    def visit_event_reference(self, node: EventReferenceNode) -> T:
        return self._default(node)

    def visit_notification(self, node: NotificationNode) -> T:
        return self._default(node)

    def visit_retry(self, node: RetryNode) -> T:
        return self._default(node)

    def visit_command(self, node: CommandNode) -> T:
        return self._default(node)

    def visit_metadata(self, node: MetadataNode) -> T:
        return self._default(node)

    def visit_unsupported(self, node: UnsupportedStatementNode) -> T:
        return self._default(node)

    def _default(self, node: object) -> T:
        """Fallback return for visitors that only care about side effects."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement visit_* methods or _default()"
        )
