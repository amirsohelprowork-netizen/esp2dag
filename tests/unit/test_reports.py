"""Unit tests for Phase 10 report generators."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.compiler.factory import build_pipeline
from esp2dag.models.config import CompileRequest, CompilerConfig
from esp2dag.reports import CompileReportGenerator
from esp2dag.reports.statistics import build_statistics


FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "mixed_ops.esp"
)


def _ensure_fixture() -> Path:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not FIXTURE.exists():
        FIXTURE.write_text(
            "APPL MIX WAIT\n"
            "JOB LIE.A EXTERNAL APPLID(OTHER)\n"
            "  RUN DAILY\n"
            "  RELEASE ADD(LIS.!ESPAPPL)\n"
            "ENDJOB\n"
            "JOB LIS.!ESPAPPL LINK PROCESS\n"
            "  RUN DAILY\n"
            "  RELEASE ADD(S1)\n"
            "ENDJOB\n"
            "SAP_JOB S1\n"
            "  AGENT SAP01\n"
            "  ABAPNAME ZPROG\n"
            "  VARIANT V1\n"
            "  RUN DAILY\n"
            "  RELEASE ADD(N1)\n"
            "ENDJOB\n"
            "NT_JOB N1\n"
            "  AGENT WIN01\n"
            "  CMDNAME D:\\RUN\\a.bat\n"
            "  RUN DAILY\n"
            "ENDJOB\n",
            encoding="utf-8",
        )
    return FIXTURE


def test_report_generator_writes_files(tmp_path: Path) -> None:
    schedule = _ensure_fixture()
    result = build_pipeline().run(
        CompileRequest(
            schedule_path=schedule,
            events_path=None,
            output_dir=tmp_path,
            options=CompilerConfig(
                emit_yaml=False,
                emit_graph=False,
                emit_reports=True,
            ),
        )
    )
    reports = tmp_path / "reports"
    assert (reports / "statistics.json").exists()
    assert (reports / "statistics.md").exists()
    assert (reports / "validation.md").exists()
    assert (reports / "migration.json").exists()
    assert (reports / "dependencies.json").exists()

    stats = json.loads((reports / "statistics.json").read_text(encoding="utf-8"))
    assert stats["total_jobs"] >= 4
    assert any("SapRfcOperator" in k for k in stats["operator_mix"])
    assert any("WinRMOperator" in k for k in stats["operator_mix"])

    deps = json.loads((reports / "dependencies.json").read_text(encoding="utf-8"))
    assert deps["edge_count"] >= 1
    assert result.workflows


def test_build_statistics_from_result(tmp_path: Path) -> None:
    schedule = _ensure_fixture()
    result = build_pipeline().run(
        CompileRequest(
            schedule_path=schedule,
            events_path=None,
            output_dir=tmp_path / "x",
            options=CompilerConfig(emit_yaml=True, emit_graph=True, emit_reports=False),
        )
    )
    data = build_statistics(result)
    assert data["successful_conversions"] == 1
    arts = CompileReportGenerator().generate(result)
    assert len(arts) == 7
