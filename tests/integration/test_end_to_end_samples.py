"""Integration tests validating end-to-end compilation of clean ESP sample estates (Levels 1-5)."""

from __future__ import annotations

from pathlib import Path
import py_compile
import yaml
from typer.testing import CliRunner

from esp2dag.cli.app import app
from esp2dag.compiler.pipeline import CompilerPipeline
from esp2dag.compiler.factory import build_pipeline
from esp2dag.models.config import CompilerConfig, CompileRequest


def test_level_1_basic_batch_compilation(tmp_path: Path) -> None:
    """Verify Level 1: Basic mainframe batch compilation to Python DAGs & YAML."""
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "01_basic_batch.esp"
    events = root / "data" / "samples" / "01_basic_events.esp"

    result = CliRunner().invoke(app, ["compile", str(schedule), str(events), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Check generated DAGs
    dags_dir = tmp_path / "dags"
    expected_dags = ["acct_daily_batch.py", "gl_posting.py", "report_distribution.py"]
    for dag_file in expected_dags:
        dag_path = dags_dir / dag_file
        assert dag_path.exists(), f"Missing expected DAG {dag_file}"
        py_compile.compile(str(dag_path), doraise=True)

    # Check YAMLs
    yaml_dir = tmp_path / "yaml"
    for yaml_file in ["acct_daily_batch.yaml", "gl_posting.yaml", "report_distribution.yaml"]:
        yaml_path = yaml_dir / yaml_file
        assert yaml_path.exists(), f"Missing expected YAML {yaml_file}"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        app_name = list(data.keys())[0]
        assert "tasks" in data[app_name]


def test_level_2_multi_platform_compilation(tmp_path: Path) -> None:
    """Verify Level 2: Multi-platform (WinRM, SSH, AS400, AIX) compilation."""
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "02_multi_platform.esp"
    events = root / "data" / "samples" / "02_multi_platform_events.esp"

    result = CliRunner().invoke(app, ["compile", str(schedule), str(events), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output

    dags_dir = tmp_path / "dags"
    expected_dags = [
        "claims_windows.py",
        "data_warehouse_etl.py",
        "legacy_policy_as400.py",
        "risk_engine_aix.py",
    ]
    for dag_file in expected_dags:
        dag_path = dags_dir / dag_file
        assert dag_path.exists()
        py_compile.compile(str(dag_path), doraise=True)
        content = dag_path.read_text(encoding="utf-8")
        assert "from airflow.sdk import DAG" in content

    # Check WinRM operator in Windows claims app
    claims_py = (dags_dir / "claims_windows.py").read_text(encoding="utf-8")
    assert "WinRMOperator" in claims_py

    # Check SSH operator in Linux ETL app
    etl_py = (dags_dir / "data_warehouse_etl.py").read_text(encoding="utf-8")
    assert "SSHOperator" in etl_py

    # Check AS400 operator in AS400 app
    as400_py = (dags_dir / "legacy_policy_as400.py").read_text(encoding="utf-8")
    assert "AS400Operator" in as400_py


def test_level_3_dependencies_and_triggers_compilation(tmp_path: Path) -> None:
    """Verify Level 3: DSTRIG, EXTERNAL, LINK, NOTWITH pools, RESOURCE."""
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "03_dependencies_and_triggers.esp"
    events = root / "data" / "samples" / "03_trigger_events.esp"

    result = CliRunner().invoke(app, ["compile", str(schedule), str(events), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output

    dags_dir = tmp_path / "dags"
    expected_dags = [
        "drug_inventory.py",
        "clinical_trials_etl.py",
        "regulatory_reporting.py",
        "supply_chain.py",
        "order_fulfillment.py",
    ]
    for dag_file in expected_dags:
        dag_path = dags_dir / dag_file
        assert dag_path.exists()
        py_compile.compile(str(dag_path), doraise=True)

    # Check ExternalTaskSensor in clinical trials
    clinical_py = (dags_dir / "clinical_trials_etl.py").read_text(encoding="utf-8")
    assert "ExternalTaskSensor" in clinical_py
    assert "external_dag_id='drug_inventory'" in clinical_py

    # Check EmptyOperator for LINK tasks
    supply_py = (dags_dir / "supply_chain.py").read_text(encoding="utf-8")
    assert "EmptyOperator" in supply_py


def test_level_4_advanced_scheduling_compilation(tmp_path: Path) -> None:
    """Verify Level 4: Advanced scheduling, GENTIME, IFHOLIDAYPLUS, bi-weekly, cyclic."""
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "04_advanced_scheduling.esp"
    events = root / "data" / "samples" / "04_scheduling_events.esp"

    result = CliRunner().invoke(app, ["compile", str(schedule), str(events), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output

    dags_dir = tmp_path / "dags"
    expected_dags = [
        "flight_ops_daily.py",
        "revenue_monthly.py",
        "loyalty_biweekly.py",
        "maintenance_cyclic.py",
        "quarterly_compliance.py",
    ]
    for dag_file in expected_dags:
        dag_path = dags_dir / dag_file
        assert dag_path.exists()
        py_compile.compile(str(dag_path), doraise=True)


def test_level_5_enterprise_production_compilation(tmp_path: Path) -> None:
    """Verify Level 5: Full 11-app enterprise estate compilation with all artifacts."""
    root = Path(__file__).resolve().parents[2]
    schedule = root / "data" / "samples" / "05_enterprise_production.esp"
    events = root / "data" / "samples" / "05_enterprise_events.esp"

    pipeline = build_pipeline()
    request = CompileRequest(
        schedule_path=schedule,
        events_path=events,
        output_dir=tmp_path,
        options=CompilerConfig(
            emit_yaml=True,
            emit_airflow=True,
            emit_graph=True,
            emit_reports=True,
        ),
    )
    result = pipeline.run(request)

    assert len(result.failures) == 0
    assert len(result.workflows) == 11
    assert result.statistics.successful_conversions == 11
    assert result.statistics.total_jobs > 70

    # Verify all 11 Python DAGs
    dags_dir = tmp_path / "dags"
    dag_files = list(dags_dir.glob("*.py"))
    assert len(dag_files) == 11
    for dag_path in dag_files:
        py_compile.compile(str(dag_path), doraise=True)

    # Verify all 11 YAMLs
    yaml_dir = tmp_path / "yaml"
    yaml_files = list(yaml_dir.glob("*.yaml"))
    assert len(yaml_files) == 11
    for yaml_path in yaml_files:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    # Verify graphs and reports
    graphs_dir = tmp_path / "graphs"
    assert len(list(graphs_dir.glob("*.mmd"))) == 11
    assert len(list(graphs_dir.glob("*.json"))) == 11

    reports_dir = tmp_path / "reports"
    assert (reports_dir / "statistics.md").exists()
    assert (reports_dir / "statistics.json").exists()
    assert (reports_dir / "migration.md").exists()
    assert (reports_dir / "validation.md").exists()
