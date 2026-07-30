"""ESP Abstract Syntax Tree node definitions.

Produced by the parser. Must not be imported by YAML/Airflow generators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.models.source import SourceSpan

if TYPE_CHECKING:
    from esp2dag.compiler.ast.visitor import AstVisitor

T = TypeVar("T")


class AstNode(BaseModel):
    """Base AST node with source span and visitor hook."""

    model_config = ConfigDict(frozen=True)

    span: SourceSpan
    node_type: str

    def accept(self, visitor: AstVisitor[T]) -> T:
        """Dispatch to the visitor method for this node type."""
        raise NotImplementedError(f"accept() not implemented for {type(self).__name__}")


class MetadataNode(AstNode):
    """Free-form key/value metadata from ESP attributes."""

    node_type: str = "metadata"
    key: str
    value: str

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_metadata(self)


class UnsupportedStatementNode(AstNode):
    """Parked unsupported ESP statement for diagnostics / manual review."""

    node_type: str = "unsupported"
    keyword: str
    raw: str
    reason: str

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_unsupported(self)


class CommandNode(AstNode):
    """Executable command associated with a job."""

    node_type: str = "command"
    text: str
    interpreter: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_command(self)


class ConditionNode(AstNode):
    """Conditional expression guarding a job or dependency."""

    node_type: str = "condition"
    expression: str
    kind: str | None = None

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_condition(self)


class DependencyNode(AstNode):
    """Predecessor relationship declared on a job."""

    node_type: str = "dependency"
    predecessor: str
    dependency_type: str | None = None
    condition: ConditionNode | None = None

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_dependency(self)


class ResourceNode(AstNode):
    """Resource definition within an application."""

    node_type: str = "resource"
    name: str
    quantity: int | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_resource(self)


class ResourceRefNode(AstNode):
    """Reference to a resource from a job."""

    node_type: str = "resource_ref"
    name: str
    quantity: int | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_resource_ref(self)


class CalendarNode(AstNode):
    """Calendar definition (opaque body in v1)."""

    node_type: str = "calendar"
    name: str
    definition: str
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_calendar(self)


class ScheduleNode(AstNode):
    """Schedule expression at application or job scope."""

    node_type: str = "schedule"
    expression: str
    calendar_ref: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_schedule(self)


class VariableNode(AstNode):
    """Variable assignment."""

    node_type: str = "variable"
    name: str
    value: str
    scope: str | None = None

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_variable(self)


class EventReferenceNode(AstNode):
    """Reference to an ESP event from the schedule side."""

    node_type: str = "event_reference"
    event_name: str
    event_kind: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_event_reference(self)


class NotificationNode(AstNode):
    """Notification / alert declaration."""

    node_type: str = "notification"
    channel: str | None = None
    recipients: list[str] = Field(default_factory=list)
    on_event: str | None = None
    message: str | None = None

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_notification(self)


class RetryNode(AstNode):
    """Retry policy on a job."""

    node_type: str = "retry"
    max_attempts: int | None = None
    interval: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_retry(self)


class JobNode(AstNode):
    """ESP job definition."""

    node_type: str = "job"
    name: str
    job_type: str | None = None
    command: CommandNode | None = None
    dependencies: list[DependencyNode] = Field(default_factory=list)
    conditions: list[ConditionNode] = Field(default_factory=list)
    resources: list[ResourceRefNode] = Field(default_factory=list)
    retry: RetryNode | None = None
    notifications: list[NotificationNode] = Field(default_factory=list)
    event_refs: list[EventReferenceNode] = Field(default_factory=list)
    schedule: ScheduleNode | None = None
    variables: list[VariableNode] = Field(default_factory=list)
    metadata: list[MetadataNode] = Field(default_factory=list)
    unsupported: list[UnsupportedStatementNode] = Field(default_factory=list)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_job(self)


class ApplicationNode(AstNode):
    """Root AST node for one ESP application."""

    node_type: str = "application"
    name: str
    jobs: list[JobNode] = Field(default_factory=list)
    calendars: list[CalendarNode] = Field(default_factory=list)
    schedules: list[ScheduleNode] = Field(default_factory=list)
    resources: list[ResourceNode] = Field(default_factory=list)
    variables: list[VariableNode] = Field(default_factory=list)
    notifications: list[NotificationNode] = Field(default_factory=list)
    metadata: list[MetadataNode] = Field(default_factory=list)
    raw_header: str | None = None
    unsupported: list[UnsupportedStatementNode] = Field(default_factory=list)

    def accept(self, visitor: AstVisitor[T]) -> T:
        return visitor.visit_application(self)
