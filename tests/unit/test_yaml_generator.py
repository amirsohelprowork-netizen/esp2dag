"""Unit tests for Phase 7 DAG Factory YAML generator (target production shape)."""

from __future__ import annotations

from pathlib import Path

import yaml

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.event_parser import EspEventMerger, EspEventParser
from esp2dag.models.source import SourceApplication, SourceFile
from esp2dag.yaml_generator import DagFactoryYamlGenerator
from esp2dag.yaml_generator.schedule_cron import esp_schedule_to_cron

EVENTS = Path(__file__).resolve().parents[1] / "fixtures" / "events" / "clean_events.esp"
DEMO_APP = Path(__file__).resolve().parents[1] / "fixtures" / "schedules" / "demo_app.esp"


def _workflow(content: str, *, name: str = "APP"):
    app = SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    return EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)


def test_esp_schedule_to_cron_dual_daily() -> None:
    raw = "11.00 DAILY STARTING FRI 17TH MAR 2023 | 19.00 DAILY STARTING FRI 17TH MAR 2023"
    assert esp_schedule_to_cron(raw) == "0 11,19 * * *"


def test_esp_schedule_to_cron_never_changes_mixed_time_pairs() -> None:
    raw = "08.03 DAILY | 09.12 DAILY"
    assert esp_schedule_to_cron(raw) is None


def test_yaml_omits_partial_schedule_instead_of_emitting_esp_text() -> None:
    wf = _workflow("APPL X\nJOB A\n  RUN !SITE_CALENDAR\nENDJOB\n", name="X")
    doc = yaml.safe_load(DagFactoryYamlGenerator().generate(wf))
    assert "schedule" not in doc["x"]


def test_yaml_emits_retry_count() -> None:
    wf = _workflow("APPL X\nNT_JOB A\n  CMDNAME D:\\a.bat\n  RETRY 3\nENDJOB\n", name="X")
    task = yaml.safe_load(DagFactoryYamlGenerator().generate(wf))["x"]["tasks"]["a"]
    assert task["retries"] == 3


def test_yaml_uses_winrm_as400_ssh_and_dependencies() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "JOB LIE.A EXTERNAL APPLID(OTHER)\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(LIS.!ESPAPPL)\n"
        "ENDJOB\n"
        "JOB LIS.!ESPAPPL LINK PROCESS\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(AS400STEP)\n"
        "ENDJOB\n"
        "AS400_JOB AS400STEP\n"
        "  RESOURCE ADD(1,RES01)\n"
        "  AGENT RES01\n"
        "  COMMAND CYBROBOT AS400STEP\n"
        "  JOBQ QUEUE01\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(MTIC)\n"
        "ENDJOB\n"
        "NT_JOB MTIC\n"
        "  AGENT AGENT02\n"
        "  CMDNAME D:\\SCRIPTS\\WINSTEP.bat\n"
        "  USER CORP\\batchuser\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(SLEEP)\n"
        "ENDJOB\n"
        "AIX_JOB SLEEP\n"
        "  AGENT AGENT03\n"
        "  COMMAND /bin/sleep\n"
        "  ARGS 3\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _workflow(content, name="DEMO")
    doc = yaml.safe_load(DagFactoryYamlGenerator().generate(wf))
    tasks = doc["demo"]["tasks"]
    assert tasks["lie_a"]["operator"].endswith("ExternalTaskSensor")
    assert tasks["lie_a"]["external_dag_id"] == "other"
    assert tasks["lie_a"]["external_task_id"] == "lie_a"
    assert tasks["lis_espappl"]["operator"].endswith("EmptyOperator")
    assert tasks["lis_espappl"]["dependencies"] == ["lie_a"]
    assert tasks["as400step"]["operator"] == "custom_operators.as400.AS400Operator"
    assert tasks["as400step"]["conn_id"] == "RES01_AS400"
    assert tasks["as400step"]["command"] == "CYBROBOT AS400STEP"
    assert tasks["mtic"]["operator"].endswith("WinRMOperator")
    assert tasks["mtic"]["ssh_conn_id"] == "AGENT02"
    assert tasks["sleep"]["operator"].endswith("SSHOperator")
    assert tasks["sleep"]["command"] == "/bin/sleep 3"
    assert doc["demo"]["default_args"]["owner"] == "batchuser"


def test_yaml_deterministic() -> None:
    content = "APPL X\nJOB A\n  RUN DAILY\n  RELEASE ADD(B)\nENDJOB\nJOB B\n  RUN DAILY\nENDJOB\n"
    wf = _workflow(content, name="X")
    gen = DagFactoryYamlGenerator()
    assert gen.generate(wf) == gen.generate(wf)


def test_yaml_maps_sap_linux_mainframe_and_applend() -> None:
    content = (
        "APPL MIX WAIT\n"
        "SAP_JOB ZREP\n"
        "  AGENT SAP_IZP100\n"
        "  SAPJOBNAME ZREP\n"
        "  SAPJOBCLASS C\n"
        "  ABAPNAME ZZREPORT\n"
        "  VARIANT V1\n"
        "  STEPUSER S_BC\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(SH)\n"
        "ENDJOB\n"
        "LINUX_JOB SH\n"
        "  AGENT LINUX01\n"
        "  COMMAND /usr/local/scripts/run.sh\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(MF)\n"
        "ENDJOB\n"
        "JOB MF\n"
        "  CCCHK RC(1:4095) OK CONTINUE\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(END)\n"
        "ENDJOB\n"
        "APPLEND END\n"
        "  RELDELAY 2\n"
        "ENDJOB\n"
        "DATA_OBJECT VARS\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "DSTRIG WAITDS\n"
        "  DSNAME 'PROD.FILE.G-'\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _workflow(content, name="MIX")
    tasks = yaml.safe_load(DagFactoryYamlGenerator().generate(wf))["mix"]["tasks"]
    assert tasks["zrep"]["operator"].endswith("SapRfcOperator")
    assert tasks["zrep"]["abap_name"] == "ZZREPORT"
    assert tasks["zrep"]["variant"] == "V1"
    assert tasks["zrep"]["conn_id"] == "SAP_IZP100"
    assert tasks["sh"]["operator"].endswith("SSHOperator")
    assert tasks["sh"]["command"] == "/usr/local/scripts/run.sh"
    assert tasks["mf"]["operator"] == "custom_operators.mainframe.MainframeSubmitJobOperator"
    assert tasks["mf"]["job_name"] == "MF"
    assert "ccchk" in tasks["mf"]
    assert tasks["end"]["operator"].endswith("EmptyOperator")
    assert tasks["vars"]["operator"].endswith("PythonOperator")
    assert tasks["waitds"]["operator"] == "custom_operators.mainframe.MainframeDatasetSensor"
    assert "PROD.FILE.G-" in tasks["waitds"]["dsname"]


def test_sampleapp_target_shape() -> None:
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
    wf = EspEventMerger().merge([wf], catalog)[0]
    doc = yaml.safe_load(DagFactoryYamlGenerator().generate(wf))
    dag = doc["sampleapp"]
    assert dag["schedule"] == "0 11,19 * * *"
    tasks = dag["tasks"]
    assert tasks["lie_upstream"]["operator"].endswith("ExternalTaskSensor")
    assert tasks["as400step"]["operator"] == "custom_operators.as400.AS400Operator"
    assert tasks["winstep"]["operator"].endswith("WinRMOperator")
    assert tasks["unixstep"]["operator"].endswith("SSHOperator")
    assert "dependencies" in tasks["as400step"]
    assert "metadata" not in tasks["as400step"]
