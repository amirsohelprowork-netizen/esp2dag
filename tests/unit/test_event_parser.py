"""Unit tests for Phase 6 event parser and merger."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.event_parser import EspEventMerger, EspEventParser
from esp2dag.models.diagnostics import DiagnosticCode
from esp2dag.models.source import SourceApplication, SourceFile
from esp2dag.models.workflow import EventKind, EventMapping, MappingStatus, TaskType

EVENTS = Path(__file__).resolve().parents[1] / "fixtures" / "events" / "clean_events.esp"
DEMO_APP = Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "demo_app.esp"


def test_parse_clean_events_catalog() -> None:
    source = SourceFile(path=EVENTS, content=EVENTS.read_text(encoding="utf-8"))
    result = EspEventParser().parse_with_diagnostics(source)
    assert len(result.catalog.events) == 3
    names = [e.name for e in result.catalog.events]
    assert "EV001.SAMPLEAPP" in names
    sample = next(e for e in result.catalog.events if e.name == "EV001.SAMPLEAPP")
    assert sample.kind == EventKind.TIME
    assert "11.00 DAILY" in sample.attributes["schedule"]
    assert sample.attributes["invoke_application"] == "SAMPLEAPP"
    assert any(b.application == "SAMPLEAPP" for b in result.catalog.bindings)


def test_parse_dstrig_file_event() -> None:
    source = SourceFile(path=EVENTS, content=EVENTS.read_text(encoding="utf-8"))
    catalog = EspEventParser().parse(source)
    file_event = next(e for e in catalog.events if e.name == "EV003.FILEDEMO")
    assert file_event.kind == EventKind.FILE
    dstrig = next(b for b in catalog.bindings if b.job == "FTPAUTO")
    assert dstrig.attributes["filepath"] == "SYNTH.DATASET.001.G-"


def test_merge_schedule_into_sampleapp_workflow() -> None:
    content = (
        "APPL SAMPLEAPP WAIT\n"
        "JOB A\n  RUN DAILY\n  RELEASE ADD(B)\nENDJOB\n"
        "JOB B\n  RUN DAILY\nENDJOB\n"
    )
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file="a.esp",
        start_line=1,
        end_line=6,
        content=content,
        header_line="APPL SAMPLEAPP WAIT",
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    wf = EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)
    catalog = EspEventParser().parse(
        SourceFile(path=EVENTS, content=EVENTS.read_text(encoding="utf-8"))
    )
    merged = EspEventMerger().merge_with_diagnostics([wf], catalog)
    out = merged.workflows[0]
    assert out.schedule is not None
    assert "11.00 DAILY" in out.schedule.raw_expression
    assert out.schedule.mapping_status == MappingStatus.MAPPED
    assert out.schedule.cron == "0 11,19 * * *"
    assert any(e.event_id == "EV001.SAMPLEAPP" for e in out.events)
    assert any(e.mapped_as == EventMapping.SCHEDULE for e in out.events)
    assert any(d.code == DiagnosticCode.W_EVENT_ORPHAN for d in merged.diagnostics)


def test_merge_dstrig_creates_sensor_task() -> None:
    content = "APPL FILEDEMO WAIT\nJOB OTHER\n  RUN DAILY\nENDJOB\n"
    app = SourceApplication(
        name="FILEDEMO",
        source_file="f.esp",
        start_line=1,
        end_line=4,
        content=content,
        header_line="APPL FILEDEMO WAIT",
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    wf = EspWorkflowBuilder().build(ast, [])
    catalog = EspEventParser().parse(
        SourceFile(path=EVENTS, content=EVENTS.read_text(encoding="utf-8"))
    )
    out = EspEventMerger().merge([wf], catalog)[0]
    sensor = next(t for t in out.tasks if t.task_id.startswith("FTPAUTO"))
    assert sensor.task_type == TaskType.SENSOR_FILE
    assert sensor.sensor is not None
    assert sensor.sensor.filepath == "SYNTH.DATASET.001.G-"


@pytest.mark.slow
def test_parse_raw_events_if_configured() -> None:
    raw = os.environ.get("ESP2DAG_RAW_EVENTS")
    if not raw:
        pytest.skip("Set ESP2DAG_RAW_EVENTS to run against private events file")
    path = Path(raw)
    if not path.exists():
        pytest.skip(f"Raw events not found: {path}")
    source = SourceFile(
        path=path,
        content=path.read_text(encoding="utf-8", errors="replace"),
    )
    result = EspEventParser().parse_with_diagnostics(source)
    assert len(result.catalog.events) >= 100


def test_merge_demo_app_fixture() -> None:
    text = DEMO_APP.read_text(encoding="utf-8")
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file=str(DEMO_APP),
        start_line=1,
        end_line=text.count("\n") + 1,
        content=text,
        header_line="APPL SAMPLEAPP WAIT",
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    wf = EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)
    catalog = EspEventParser().parse(
        SourceFile(path=EVENTS, content=EVENTS.read_text(encoding="utf-8"))
    )
    out = EspEventMerger().merge([wf], catalog)[0]
    assert any(e.event_id == "EV001.SAMPLEAPP" for e in out.events)
    assert out.schedule is not None
    assert "11.00 DAILY" in (out.schedule.raw_expression or "")
