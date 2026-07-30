"""Unit tests for Phase 4 semantic analyzer."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.models.diagnostics import DiagnosticCode, Severity
from esp2dag.models.source import SourceApplication

DEMO_APP = Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "demo_app.esp"


def _analyze(content: str, *, name: str = "APP") -> object:
    app = SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    return EspSemanticAnalyzer().analyze(ast)


def test_duplicate_job_error() -> None:
    content = (
        "APPL X\n"
        "JOB A\n  RUN DAILY\nENDJOB\n"
        "JOB A\n  RUN DAILY\nENDJOB\n"
    )
    result = _analyze(content)
    assert any(d.code == DiagnosticCode.E_SEM_DUPLICATE_JOB for d in result.diagnostics)
    assert result.has_errors


def test_circular_release_cycle() -> None:
    content = (
        "APPL X\n"
        "JOB A\n  RUN DAILY\n  RELEASE ADD(B)\nENDJOB\n"
        "JOB B\n  RUN DAILY\n  RELEASE ADD(A)\nENDJOB\n"
    )
    result = _analyze(content)
    assert any(d.code == DiagnosticCode.E_SEM_CIRCULAR_DEP for d in result.diagnostics)


def test_missing_release_target_warning() -> None:
    content = (
        "APPL X\n"
        "JOB A\n  RUN DAILY\n  RELEASE ADD(MISSING_JOB)\nENDJOB\n"
    )
    result = _analyze(content)
    misses = [d for d in result.diagnostics if d.code == DiagnosticCode.E_SEM_MISSING_PRED]
    assert misses
    assert misses[0].severity == Severity.WARNING


def test_runtime_symbol_release_ok() -> None:
    content = (
        "APPL X\n"
        "JOB A\n  RUN DAILY\n  RELEASE ADD(LIS.!ESPAPPL)\nENDJOB\n"
    )
    result = _analyze(content)
    assert not any(d.code == DiagnosticCode.E_SEM_MISSING_PRED for d in result.diagnostics)


def test_external_applid_ok() -> None:
    content = (
        "APPL X\n"
        "JOB LIE.A EXTERNAL APPLID(OTHER)\n  RUN DAILY\nENDJOB\n"
    )
    result = _analyze(content)
    assert not any(d.code == DiagnosticCode.E_SEM_INVALID_REF for d in result.diagnostics)


def test_external_without_applid_warns() -> None:
    content = (
        "APPL X\n"
        "JOB LIE.A EXTERNAL\n  RUN DAILY\nENDJOB\n"
    )
    result = _analyze(content)
    assert any(d.code == DiagnosticCode.E_SEM_INVALID_REF for d in result.diagnostics)


def test_empty_application_warns() -> None:
    content = "APPL EMPTY WAIT\n"
    result = _analyze(content, name="EMPTY")
    assert any(d.severity == Severity.WARNING for d in result.diagnostics)


def test_unsupported_promoted() -> None:
    content = (
        "APPL X\n"
        "WEIRDSTMT FOO\n"
        "JOB A\n  RUN DAILY\nENDJOB\n"
    )
    result = _analyze(content)
    assert any(d.code == DiagnosticCode.W_SEM_UNSUPPORTED for d in result.diagnostics)


def test_batch_duplicate_applications() -> None:
    content = "APPL SAME\nJOB A\n  RUN DAILY\nENDJOB\n"
    app1 = SourceApplication(
        name="SAME",
        source_file="a.esp",
        start_line=1,
        end_line=4,
        content=content,
        header_line="APPL SAME",
    )
    app2 = SourceApplication(
        name="SAME",
        source_file="b.esp",
        start_line=10,
        end_line=14,
        content=content,
        header_line="APPL SAME",
    )
    ast1 = EspParser().parse(EspLexer().tokenize(app1), app1)
    ast2 = EspParser().parse(EspLexer().tokenize(app2), app2)
    # Force distinct spans for messaging
    diags = EspSemanticAnalyzer().analyze_batch([ast1, ast2])
    assert any(d.code == DiagnosticCode.E_SEM_DUPLICATE_APP for d in diags)


def test_sampleapp_has_no_semantic_errors() -> None:
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
    result = EspSemanticAnalyzer().analyze(ast)
    errors = [d for d in result.diagnostics if d.severity == Severity.ERROR]
    assert errors == []
