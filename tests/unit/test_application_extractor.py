"""Unit tests for Phase 1 Application Extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from esp2dag.extractor import ApplicationExtractor, strip_esp_comments
from esp2dag.extractor.writer import application_filename, write_extract_artifacts
from esp2dag.models.diagnostics import DiagnosticCode, Severity
from esp2dag.models.source import SourceFile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schedules"


def _load(name: str) -> SourceFile:
    path = FIXTURES / name
    return SourceFile(path=path, content=path.read_text(encoding="utf-8"))


def test_strip_esp_comments_inline_and_eol() -> None:
    code, in_block = strip_esp_comments("JOB A /* note */ RUN", False)
    assert code == "JOB A  RUN"
    assert in_block is False

    code, in_block = strip_esp_comments("before /* start", False)
    assert code == "before "
    assert in_block is False

    # Unclosed /* must not poison the next line.
    code, in_block = strip_esp_comments("APPL NEXT", True)
    assert code.strip() == "APPL NEXT"
    assert in_block is False


def test_extract_multi_app_preserves_lines_and_names() -> None:
    result = ApplicationExtractor().extract(_load("sample_multi_app.esp"))
    assert [a.name for a in result.applications] == ["APP_A", "APP_B"]
    app_a, app_b = result.applications
    assert app_a.start_line == 4
    assert app_a.end_line == 8  # includes blank line before next APPL
    assert app_a.content.startswith("APPL APP_A WAIT")
    assert "JOB JOB1" in app_a.content
    assert app_b.start_line == 9
    assert "JOB JOB_X" in app_b.content
    assert app_a.source_file.endswith("sample_multi_app.esp")
    prologue = [d for d in result.diagnostics if d.code == DiagnosticCode.W_EXTRACT_PROLOGUE]
    assert len(prologue) == 1


def test_extract_empty_application_warns() -> None:
    result = ApplicationExtractor().extract(_load("empty_app.esp"))
    assert len(result.applications) == 1
    assert result.applications[0].name == "ONLY_HEADER"
    assert any(d.code == DiagnosticCode.W_EXTRACT_EMPTY_APP for d in result.diagnostics)


def test_extract_ignores_appl_in_comments_and_arguments() -> None:
    result = ApplicationExtractor().extract(_load("comments_and_false_positives.esp"))
    assert [a.name for a in result.applications] == ["REAL1", "REAL2"]
    assert "COMPLETE APPL(OTHER.0)" in result.applications[1].content


def test_extract_duplicate_names_keeps_both_units() -> None:
    result = ApplicationExtractor().extract(_load("duplicate_names.esp"))
    assert [a.name for a in result.applications] == ["DUPAPP", "OTHER", "DUPAPP"]
    dup_warnings = [
        d for d in result.diagnostics if d.code == DiagnosticCode.W_EXTRACT_DUPLICATE_NAME
    ]
    assert len(dup_warnings) == 1
    assert dup_warnings[0].span is not None
    assert dup_warnings[0].span.start_line == 7


def test_extract_endappl_orphan_and_interstitial() -> None:
    result = ApplicationExtractor().extract(_load("endappl_and_orphan.esp"))
    assert [a.name for a in result.applications] == ["REALAPP", "NEXTAPP"]
    codes = {d.code for d in result.diagnostics}
    assert DiagnosticCode.E_EXTRACT_ORPHAN_ENDAPPL in codes
    assert DiagnosticCode.W_EXTRACT_PROLOGUE in codes
    assert DiagnosticCode.W_EXTRACT_INTERSTITIAL in codes
    real = result.applications[0]
    assert real.end_line == 10  # ENDAPPL line
    assert "ENDAPPL" in real.content


def test_extract_no_apps_is_error() -> None:
    source = SourceFile(path=Path("none.esp"), content="/* only comments */\nNORUN JAN 1 2024\n")
    result = ApplicationExtractor().extract(source)
    assert result.applications == []
    assert any(d.code == DiagnosticCode.E_EXTRACT_NO_APPS for d in result.diagnostics)
    assert any(d.severity == Severity.ERROR for d in result.diagnostics)


def test_extract_empty_file_is_error() -> None:
    result = ApplicationExtractor().extract(SourceFile(path=Path("empty.esp"), content=""))
    assert result.applications == []
    assert any(d.code == DiagnosticCode.E_EXTRACT_NO_APPS for d in result.diagnostics)


def test_extract_supports_application_keyword_and_endappl() -> None:
    content = "APPLICATION LEGACY_A\n  JOB J\nENDAPPL\nAPPLICATION LEGACY_B\nENDAPPL\n"
    result = ApplicationExtractor().extract(SourceFile(path=Path("legacy.esp"), content=content))
    assert [a.name for a in result.applications] == ["LEGACY_A", "LEGACY_B"]
    assert result.applications[0].content.strip().endswith("ENDAPPL")


def test_extract_sample_slice_real_syntax() -> None:
    result = ApplicationExtractor().extract(_load("sample_agent_slice.esp"))
    names = [a.name for a in result.applications]
    assert names == ["SAMPLEA", "SAMPLEB", "SAMPLEC"]
    abd = result.applications[0]
    assert abd.start_line == 1
    assert "JOB SAMPLEJOB" in abd.content
    assert abd.content.startswith("APPL SAMPLEA WAIT")
    # SAMPLEB body contains COMPLETE APPL(...) which must not split apps
    assert "COMPLETE APPL(OTHERAPP.0)" in result.applications[1].content
    assert any(d.code == DiagnosticCode.W_EXTRACT_EMPTY_APP for d in result.diagnostics)


def test_writer_manifest_deterministic(tmp_path: Path) -> None:
    result = ApplicationExtractor().extract(_load("sample_multi_app.esp"))
    written = write_extract_artifacts(result, tmp_path)
    assert (tmp_path / "manifest.json").exists()
    assert application_filename(result.applications[0]) == "APP_A__L4.esp"
    text1 = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    write_extract_artifacts(result, tmp_path)
    text2 = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert text1 == text2
    assert any(p.name.endswith(".esp") for p in written)


@pytest.mark.slow
def test_extract_full_raw_schedule_if_configured() -> None:
    import os

    raw = os.environ.get("ESP2DAG_RAW_SCHEDULE")
    if not raw:
        pytest.skip("Set ESP2DAG_RAW_SCHEDULE to run against a private full schedule")
    path = Path(raw)
    if not path.exists():
        pytest.skip(f"Raw schedule not found: {path}")
    source = SourceFile(path=path, content=path.read_text(encoding="utf-8", errors="replace"))
    result = ApplicationExtractor().extract(source)
    assert len(result.applications) >= 100
    for app in result.applications[:20]:
        first = app.content.lstrip("\ufeff").splitlines()[0].strip()
        assert first.upper().startswith("APPL")
