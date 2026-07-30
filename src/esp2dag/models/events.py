"""ESP event domain models (pre-merge catalog)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.models.source import SourceSpan, SourceTrace
from esp2dag.models.workflow import EventKind


class EventDefinition(BaseModel):
    """A single event definition from the ESP events file."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: EventKind
    attributes: dict[str, str] = Field(default_factory=dict)
    span: SourceSpan
    raw: str | None = None


class EventJobBinding(BaseModel):
    """Association between an event and an application/job."""

    model_config = ConfigDict(frozen=True)

    event_name: str
    application: str | None = None
    job: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    span: SourceSpan
    trace: SourceTrace | None = None


class EventCatalog(BaseModel):
    """Parsed events file contents prior to workflow merge."""

    model_config = ConfigDict(frozen=True)

    source_file: str
    events: list[EventDefinition] = Field(default_factory=list)
    bindings: list[EventJobBinding] = Field(default_factory=list)

    def events_by_name(self) -> dict[str, EventDefinition]:
        """Index events by name (last definition wins; merger may warn on dupes)."""
        return {event.name: event for event in self.events}
