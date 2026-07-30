"""Unit tests for domain models and utilities (foundation)."""

from __future__ import annotations

from pathlib import Path

from esp2dag.models import (
    CompileResult,
    CompilerConfig,
    SourceApplication,
    SourceFile,
    SourceSpan,
    SourceTrace,
    Task,
    TaskType,
    Workflow,
    WorkflowMetadata,
)
from esp2dag.utils import sanitize_task_id


def test_source_application_span() -> None:
    app = SourceApplication(
        name="APP_A",
        source_file="/schedules/prod.esp",
        start_line=10,
        end_line=40,
        content="APPLICATION APP_A\nENDAPPL\n",
        header_line="APPLICATION APP_A",
    )
    assert app.span.start_line == 10
    assert app.span.end_line == 40
    assert app.span.file == "/schedules/prod.esp"


def test_source_trace_from_span() -> None:
    span = SourceSpan(file="a.esp", start_line=5, start_column=1, end_line=5, end_column=10, text="JOB X")
    trace = SourceTrace.from_span(application="APP_A", job="X", span=span)
    assert trace.source_application == "APP_A"
    assert trace.source_job == "X"
    assert trace.source_line == 5


def test_sanitize_task_id_deterministic() -> None:
    assert sanitize_task_id("JOB-1") == "JOB_1"
    assert sanitize_task_id("123ABC") == "t_123ABC"
    assert sanitize_task_id("@@@") == "task"
    assert sanitize_task_id("JOB-1") == sanitize_task_id("JOB-1")


def test_workflow_requires_trace_on_task() -> None:
    span = SourceSpan(file="a.esp", start_line=1, end_line=1)
    meta = WorkflowMetadata(
        source_application="APP_A",
        source_file="a.esp",
        source_span=span,
    )
    trace = SourceTrace(
        source_file="a.esp",
        source_application="APP_A",
        source_job="JOB1",
        source_line=2,
    )
    wf = Workflow(
        id="app_a",
        name="APP_A",
        metadata=meta,
        tasks=[
            Task(task_id="job1", name="JOB1", task_type=TaskType.EMPTY, trace=trace),
        ],
    )
    assert wf.task_ids() == ["job1"]


def test_compile_result_ok_when_empty() -> None:
    result = CompileResult()
    assert result.ok is True


def test_source_file_path_str() -> None:
    sf = SourceFile(path=Path("sched.esp"), content="APPLICATION X\nENDAPPL\n")
    assert "sched.esp" in sf.path_str


def test_compiler_config_defaults() -> None:
    cfg = CompilerConfig()
    assert cfg.emit_yaml is True
    assert cfg.emit_airflow is False
    assert cfg.continue_on_error is True
