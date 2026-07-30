"""Unit tests for Phase 5 Workflow IR builder."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder, TaskIdAllocator, workflow_summary
from esp2dag.models.source import SourceApplication
from esp2dag.models.workflow import TaskType

DEMO_APP = Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "demo_app.esp"


def _build(content: str, *, name: str = "APP"):
    app = SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    semantic = EspSemanticAnalyzer().analyze(ast)
    return EspWorkflowBuilder().build(ast, semantic.diagnostics)


def test_task_id_allocator_collisions() -> None:
    alloc = TaskIdAllocator()
    assert alloc.allocate("JOB-1") == "JOB_1"
    assert alloc.allocate("JOB_1") == "JOB_1_2"  # different job name sanitizes same? 
    # Actually JOB_1 as name sanitizes to JOB_1, collision with previous base
    # Wait - first was JOB-1 → JOB_1. Second job name JOB_1 → JOB_1 → collision → JOB_1_2
    assert alloc.resolve("JOB-1") == "JOB_1"


def test_build_release_edges_and_bash_task() -> None:
    content = (
        "APPL APP_A WAIT\n"
        "NT_JOB JOB1\n"
        "  CMDNAME D:\\RUN\\A.bat\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(JOB2)\n"
        "ENDJOB\n"
        "JOB JOB2\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _build(content, name="APP_A")
    assert wf.id == "app_a"
    assert [t.task_id for t in wf.tasks] == ["JOB1", "JOB2"]
    assert wf.tasks[0].task_type == TaskType.BASH
    assert wf.tasks[1].task_type == TaskType.BASH  # z/OS JOB → mainframe operator
    assert wf.dependencies[0].upstream_task_id == "JOB1"
    assert wf.dependencies[0].downstream_task_id == "JOB2"
    assert wf.tasks[0].trace.source_application == "APP_A"
    assert wf.tasks[0].trace.source_job == "JOB1"
    assert wf.schedule is not None
    assert wf.schedule.cron == "0 0 * * *"


def test_external_job_becomes_sensor() -> None:
    content = (
        "APPL X\n"
        "JOB LIE.A EXTERNAL APPLID(OTHER)\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(NEXT)\n"
        "ENDJOB\n"
        "JOB NEXT\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _build(content)
    ext = wf.tasks[0]
    assert ext.task_type == TaskType.SENSOR_EXTERNAL
    assert ext.sensor is not None
    assert ext.sensor.external_dag_id == "OTHER"
    assert wf.events
    assert wf.events[0].event_id == "OTHER"


def test_resource_becomes_pool() -> None:
    content = (
        "APPL X\n"
        "AS400_JOB A\n"
        "  RESOURCE ADD(1,RES01)\n"
        "  COMMAND CYBROBOT A\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _build(content)
    assert wf.tasks[0].pool == "RES01"
    assert any(r.name == "RES01" for r in wf.resources)


def test_every_task_has_trace() -> None:
    content = (
        "APPL X\n"
        "JOB A\n  RUN DAILY\nENDJOB\n"
        "JOB B\n  RUN DAILY\nENDJOB\n"
    )
    wf = _build(content)
    assert all(t.trace.source_line >= 1 for t in wf.tasks)
    assert all(t.trace.source_file == "test.esp" for t in wf.tasks)


def test_sampleapp_workflow_ir() -> None:
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
    semantic = EspSemanticAnalyzer().analyze(ast)
    wf = EspWorkflowBuilder().build(ast, semantic.diagnostics)
    summary = workflow_summary(wf)
    assert summary["name"] == "SAMPLEAPP"
    assert summary["task_count"] == 5
    assert summary["dependency_count"] >= 4
    ups = {(d.upstream_task_id, d.downstream_task_id) for d in wf.dependencies}
    assert ("AS400STEP", "WINSTEP") in ups
    assert ("WINSTEP", "UNIXSTEP") in ups
    assert wf.tasks[0].trace.source_line >= 1
