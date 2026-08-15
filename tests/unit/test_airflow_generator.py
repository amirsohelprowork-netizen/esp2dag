"""Tests for native Apache Airflow 3 DAG generation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from esp2dag.airflow_generator import AirflowDagGenerator
from esp2dag.cli.app import app
from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.models.source import SourceApplication


def _workflow(content: str, *, name: str = "APP"):
    source = SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(source), source)
    return EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)


def test_generates_compilable_airflow_3_module() -> None:
    workflow = _workflow(
        "APPL PAYROLL\n"
        "NT_JOB EXTRACT\n"
        "  AGENT WINDOWS01\n"
        "  CMDNAME C:\\Payroll\\extract.cmd\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(TRANSFORM)\n"
        "ENDJOB\n"
        "LINUX_JOB TRANSFORM\n"
        "  AGENT LINUX01\n"
        "  SCRIPTNAME /opt/payroll/transform.sh\n"
        "  ARGS --date {{ ds }}\n"
        "  RETRY 2\n"
        "  RUN DAILY\n"
        "ENDJOB\n",
        name="PAYROLL",
    )

    generated = AirflowDagGenerator().generate(workflow)

    compile(generated, "payroll.py", "exec")
    assert "from airflow.sdk import DAG" in generated
    assert (
        "from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator"
        in generated
    )
    assert "from airflow.providers.ssh.operators.ssh import SSHOperator" in generated
    assert "schedule='@daily'" in generated
    assert "tasks['extract'] >> tasks['transform']" in generated
    assert "retries=2" in generated
    assert "ESP source: test.esp:" in generated


def test_keeps_calendar_dependent_schedule_unscheduled() -> None:
    workflow = _workflow(
        "APPL CALENDAR\nJOB A\n  RUN MONDAY LESS 0 WORKDAYS\nENDJOB\n",
        name="CALENDAR",
    )

    generated = AirflowDagGenerator().generate(workflow)

    assert "schedule=None" in generated
    assert "Schedule requires migration review: MONDAY LESS 0 WORKDAYS" in generated


def test_cli_writes_native_dag_for_cookbook_inspired_sample(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "01_basic_batch.esp"
    events = root / "data" / "samples" / "01_basic_events.esp"

    result = CliRunner().invoke(app, ["dag", str(schedule), str(events), "-o", str(tmp_path)])

    assert result.exit_code == 0, result.output
    dag_path = tmp_path / "dags" / "acct_daily_batch.py"
    assert dag_path.exists()
    generated = dag_path.read_text(encoding="utf-8")
    compile(generated, str(dag_path), "exec")
    assert "schedule='0 22 * * *'" in generated
    assert "tasks['extract_transactions'] >> tasks['validate_data']" in generated

