"""ESP events file parser — Phase 6a.

Parses Broadcom ESP ``EVENT ID(...) ... ENDDEF`` definitions (including
schedule and dataset-trigger forms) into an ``EventCatalog``.
"""

from __future__ import annotations

import logging
import re

from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity
from esp2dag.models.events import EventCatalog, EventDefinition, EventJobBinding
from esp2dag.models.source import SourceFile, SourceSpan, SourceTrace
from esp2dag.models.workflow import EventKind
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

STAGE = "event_parser"

_EVENT_ID_RE = re.compile(r"\bEVENT\s+ID\(([^)]+)\)", re.IGNORECASE)
_ATTR_RE = re.compile(r"\b([A-Z][A-Z0-9_]*)\(([^)]*)\)", re.IGNORECASE)
_INVOKE_RE = re.compile(
    r"\bINVOKE\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))",
    re.IGNORECASE,
)
_INVOKE_APPL_RE = re.compile(r"\(([^()]+)\)\s*$")
_SCHEDULE_RE = re.compile(r"^\s*SCHEDULE\b(.*)$", re.IGNORECASE)
_CALENDAR_RE = re.compile(r"^\s*CALENDAR\s+(\S+)", re.IGNORECASE)
_DSTRIG_RE = re.compile(
    r"\bDSTRIG\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))\s+JOB\(([^)]+)\)",
    re.IGNORECASE,
)
_ENDDEF_RE = re.compile(r"^\s*ENDDEF\b", re.IGNORECASE)


class EventParseResult(BaseModel):
    """Catalog plus diagnostics from events parsing."""

    model_config = ConfigDict(frozen=True)

    catalog: EventCatalog
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class EspEventParser:
    """Parse an ESP events export into ``EventCatalog``."""

    def parse(self, source: SourceFile) -> EventCatalog:
        """Parse events file (protocol entrypoint)."""
        return self.parse_with_diagnostics(source).catalog

    def parse_with_diagnostics(self, source: SourceFile) -> EventParseResult:
        """Parse events and return catalog + diagnostics."""
        logger.info("Parsing events file %s", source.path_str)
        lines = _normalize_lines(source.content)
        joined = _join_continuations(lines)

        events: list[EventDefinition] = []
        bindings: list[EventJobBinding] = []
        diagnostics: list[Diagnostic] = []

        blocks = _split_event_blocks(joined, source.path_str)
        if not blocks:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.E_EVENT_PARSE,
                    severity=Severity.ERROR,
                    message="No EVENT ID(...) ... ENDDEF blocks found in events file.",
                    stage=STAGE,
                    span=SourceSpan(
                        file=source.path_str, start_line=1, end_line=max(1, len(lines))
                    ),
                )
            )

        for block in blocks:
            try:
                event, event_bindings = _parse_block(block, source.path_str)
                events.append(event)
                bindings.extend(event_bindings)
            except Exception as exc:  # noqa: BLE001 - isolate per event
                logger.exception("Failed to parse event block at line %s", block.start_line)
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCode.E_EVENT_PARSE,
                        severity=Severity.ERROR,
                        message=f"Failed to parse event block: {exc}",
                        stage=STAGE,
                        span=SourceSpan(
                            file=source.path_str,
                            start_line=block.start_line,
                            end_line=block.end_line,
                        ),
                    )
                )

        catalog = EventCatalog(
            source_file=source.path_str,
            events=events,
            bindings=bindings,
        )
        logger.info(
            "Parsed %d event(s), %d binding(s) from %s",
            len(events),
            len(bindings),
            source.path_str,
        )
        return EventParseResult(catalog=catalog, diagnostics=diagnostics)


class _EventBlock:
    __slots__ = ("start_line", "end_line", "text")

    def __init__(self, start_line: int, end_line: int, text: str) -> None:
        self.start_line = start_line
        self.end_line = end_line
        self.text = text


def _normalize_lines(content: str) -> list[str]:
    """Strip BOM, Excel Column1 header, and trailing tabs."""
    text = content.lstrip("\ufeff")
    raw_lines = text.splitlines()
    lines: list[str] = []
    for index, line in enumerate(raw_lines):
        cleaned = line.rstrip("\r\n").rstrip("\t")
        if index == 0 and cleaned.strip().upper() in {"COLUMN1", "COLUMN1,"}:
            continue
        # Drop empty trailing-tab-only artifacts already handled; keep content.
        lines.append(cleaned)
    return lines


def _join_continuations(lines: list[str]) -> list[tuple[int, str]]:
    """Join ESP '-' continuations; return (start_line_number, logical_line)."""
    result: list[tuple[int, str]] = []
    buffer = ""
    start_line = 1
    for line_no, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if not buffer:
            start_line = line_no
        if stripped.endswith("-") and not stripped.strip().startswith("/*"):
            buffer += stripped[:-1].rstrip() + " "
            continue
        buffer += stripped
        if buffer.strip():
            result.append((start_line, buffer))
        buffer = ""
    if buffer.strip():
        result.append((start_line, buffer))
    return result


def _split_event_blocks(
    joined: list[tuple[int, str]],
    source_file: str,
) -> list[_EventBlock]:
    _ = source_file
    blocks: list[_EventBlock] = []
    collecting = False
    start_line = 1
    parts: list[str] = []
    end_line = 1

    for line_no, text in joined:
        if _EVENT_ID_RE.search(text):
            if collecting and parts:
                blocks.append(_EventBlock(start_line, end_line, "\n".join(parts)))
            collecting = True
            start_line = line_no
            parts = [text]
            end_line = line_no
            if _ENDDEF_RE.search(text):
                blocks.append(_EventBlock(start_line, end_line, "\n".join(parts)))
                collecting = False
                parts = []
            continue
        if collecting:
            parts.append(text)
            end_line = line_no
            if _ENDDEF_RE.search(text):
                blocks.append(_EventBlock(start_line, end_line, "\n".join(parts)))
                collecting = False
                parts = []
    if collecting and parts:
        blocks.append(_EventBlock(start_line, end_line, "\n".join(parts)))
    return blocks


def _parse_block(
    block: _EventBlock,
    source_file: str,
) -> tuple[EventDefinition, list[EventJobBinding]]:
    text = block.text
    id_match = _EVENT_ID_RE.search(text)
    if not id_match:
        raise ValueError("EVENT ID(...) missing")
    event_name = id_match.group(1).strip()

    attributes: dict[str, str] = {}
    for match in _ATTR_RE.finditer(text):
        key = match.group(1).upper()
        if key == "ID":
            continue
        attributes[key.lower()] = match.group(2).strip()

    schedules: list[str] = []
    calendar: str | None = None
    invoke_raw: str | None = None
    invoke_appl: str | None = None
    dstrigs: list[tuple[str, str]] = []

    for line in text.splitlines():
        cal = _CALENDAR_RE.match(line)
        if cal:
            calendar = cal.group(1).strip()
            continue
        sch = _SCHEDULE_RE.match(line)
        if sch:
            schedules.append(sch.group(1).strip())
            continue
        inv = _INVOKE_RE.search(line)
        if inv:
            invoke_raw = next(g for g in inv.groups() if g)
            appl_match = _INVOKE_APPL_RE.search(invoke_raw)
            invoke_appl = appl_match.group(1).strip() if appl_match else invoke_raw
            continue
        for ds in _DSTRIG_RE.finditer(line):
            path = next(g for g in ds.groups()[:3] if g)
            job = ds.group(4).strip()
            dstrigs.append((path, job))

    if calendar:
        attributes["calendar"] = calendar
    if schedules:
        attributes["schedule"] = " | ".join(schedules)
    if invoke_raw:
        attributes["invoke"] = invoke_raw
    if invoke_appl:
        attributes["invoke_application"] = invoke_appl
    if "REPLACE" in text.upper():
        attributes["replace"] = "true"

    kind = _infer_kind(schedules, dstrigs, attributes)
    span = SourceSpan(
        file=source_file,
        start_line=block.start_line,
        end_line=block.end_line,
        text=f"EVENT ID({event_name})",
    )
    event = EventDefinition(
        name=event_name,
        kind=kind,
        attributes=attributes,
        span=span,
        raw=text,
    )

    bindings: list[EventJobBinding] = []
    if invoke_appl:
        bindings.append(
            EventJobBinding(
                event_name=event_name,
                application=invoke_appl,
                job=None,
                attributes={"via": "invoke"},
                span=span,
                trace=SourceTrace(
                    source_file=source_file,
                    source_application=invoke_appl,
                    source_job=None,
                    source_line=block.start_line,
                    source_statement=f"INVOKE {invoke_raw}",
                ),
            )
        )
    for path, job in dstrigs:
        bindings.append(
            EventJobBinding(
                event_name=event_name,
                application=invoke_appl,
                job=job,
                attributes={"via": "dstrig", "filepath": path},
                span=span,
                trace=SourceTrace(
                    source_file=source_file,
                    source_application=invoke_appl or event_name,
                    source_job=job,
                    source_line=block.start_line,
                    source_statement=f"DSTRIG {path} JOB({job})",
                ),
            )
        )
    return event, bindings


def _infer_kind(
    schedules: list[str],
    dstrigs: list[tuple[str, str]],
    attributes: dict[str, str],
) -> EventKind:
    if dstrigs:
        return EventKind.FILE
    if schedules:
        return EventKind.TIME
    if attributes.get("invoke_application"):
        return EventKind.APPLICATION
    return EventKind.TRIGGER
