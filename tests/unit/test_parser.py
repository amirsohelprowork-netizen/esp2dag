"""Unit tests for Phase 3 ESP parser."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser, application_summary
from esp2dag.extractor import ApplicationExtractor
from esp2dag.models.diagnostics import DiagnosticCode
from esp2dag.models.source import SourceApplication, SourceFile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schedules"
DEMO_APP = Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "demo_app.esp"


def _parse_text(content: str, *, start_line: int = 1, name: str = "T") -> object:
    app = SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=start_line,
        end_line=start_line + max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    tokens = EspLexer().tokenize(app)
    return EspParser().parse_with_diagnostics(tokens, app)


def test_parse_simple_appl_jobs_and_release() -> None:
    content = (
        "APPL APP_A WAIT\n"
        "JOB JOB1\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(JOB2)\n"
        "ENDJOB\n"
        "JOB JOB2\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content, name="APP_A")
    assert result.ast.name == "APP_A"
    assert [j.name for j in result.ast.jobs] == ["JOB1", "JOB2"]
    assert result.ast.jobs[0].schedule is not None
    assert result.ast.jobs[0].schedule.expression == "DAILY"
    assert result.ast.jobs[0].dependencies[0].predecessor == "JOB2"
    assert result.ast.jobs[0].dependencies[0].dependency_type == "RELEASE"


def test_parse_after_add_dependency() -> None:
    content = (
        "APPL APP_A WAIT\n"
        "JOB JOB1\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "JOB JOB2\n"
        "  RUN DAILY\n"
        "  AFTER ADD(JOB1)\n"
        "ENDJOB\n"
    )
    result = _parse_text(content, name="APP_A")
    dep = result.ast.jobs[1].dependencies[0]
    assert dep.predecessor == "JOB1"
    assert dep.dependency_type == "AFTER"


def test_parse_job_types_and_command() -> None:
    content = (
        "APPL X\n"
        "NT_JOB FOO\n"
        "  AGENT BOX\n"
        "  CMDNAME D:\\RUN\\FOO.bat\n"
        "  USER CORP\\batchuser\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    job = result.ast.jobs[0]
    assert job.job_type == "NT_JOB"
    assert job.command is not None
    assert "FOO.bat" in job.command.text
    assert any(m.key == "agent" and m.value == "BOX" for m in job.metadata)


def test_parse_external_applid() -> None:
    content = (
        "APPL X\n"
        "JOB LIE.UPSTREAM EXTERNAL APPLID(OTHERAPP)\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    job = result.ast.jobs[0]
    assert any(m.key == "external" for m in job.metadata)
    assert job.event_refs[0].event_name == "OTHERAPP"


def test_parse_resource_add() -> None:
    content = (
        "APPL X\n"
        "AS400_JOB A\n"
        "  RESOURCE ADD(1,RES01)\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    ref = result.ast.jobs[0].resources[0]
    assert ref.name == "RES01"
    assert ref.quantity == 1


def test_parse_notify_and_tag() -> None:
    content = (
        "APPL X\n"
        "NOTIFY FAILURE ABEND ALERT(ALERT01)\n"
        "TAG DEMOTAG\n"
        "JOB A\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    assert result.ast.notifications
    assert result.ast.notifications[0].recipients == ["ALERT01"]
    assert any(m.key == "tag" and m.value == "DEMOTAG" for m in result.ast.metadata)


def test_parse_missing_endjob_recovers() -> None:
    content = (
        "APPL X\n"
        "JOB A\n"
        "  RUN DAILY\n"
        "JOB B\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    assert len(result.ast.jobs) == 2
    assert any(d.code == DiagnosticCode.E_PARSE_MISSING_TOKEN for d in result.diagnostics)


def test_parse_unsupported_parked() -> None:
    content = (
        "APPL X\n"
        "WEIRDSTMT FOO BAR\n"
        "JOB A\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    assert result.ast.unsupported
    assert result.ast.unsupported[0].keyword == "WEIRDSTMT"
    assert any(d.code == DiagnosticCode.W_PARSE_UNSUPPORTED for d in result.diagnostics)


def test_parse_data_object_setvar() -> None:
    content = (
        "APPL X\n"
        "DATA_OBJECT PARMSET.!ESPAPPL\n"
        "   SETVAR PID='1'\n"
        "ENDJOB\n"
    )
    result = _parse_text(content)
    job = result.ast.jobs[0]
    assert job.job_type == "DATA_OBJECT"
    assert job.variables[0].name == "PID"
    assert job.variables[0].value == "1"


def test_parse_fixture_sample() -> None:
    source = SourceFile(
        path=FIXTURES / "sample_multi_app.esp",
        content=(FIXTURES / "sample_multi_app.esp").read_text(encoding="utf-8"),
    )
    app = ApplicationExtractor().extract(source).applications[0]
    result = EspParser().parse_with_diagnostics(EspLexer().tokenize(app), app)
    assert result.ast.name == "APP_A"
    assert len(result.ast.jobs) >= 1


def test_parse_demo_app() -> None:
    text = DEMO_APP.read_text(encoding="utf-8")
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file=str(DEMO_APP),
        start_line=1,
        end_line=text.count("\n") + 1,
        content=text,
        header_line="APPL SAMPLEAPP WAIT",
    )
    result = EspParser().parse_with_diagnostics(EspLexer().tokenize(app), app)
    summary = application_summary(result.ast)
    assert summary["name"] == "SAMPLEAPP"
    assert summary["job_count"] >= 5
    names = [j["name"] for j in summary["jobs"]]  # type: ignore[index]
    assert "AS400STEP" in names
    assert "WINSTEP" in names
    winstep = next(j for j in result.ast.jobs if j.name == "WINSTEP")
    assert any(d.predecessor == "UNIXSTEP" for d in winstep.dependencies)
