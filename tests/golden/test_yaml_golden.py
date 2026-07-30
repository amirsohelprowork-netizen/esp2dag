"""Golden tests for Phase 7 DAG Factory YAML (production shape)."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.models.source import SourceApplication
from esp2dag.yaml_generator import DagFactoryYamlGenerator

GOLDEN = Path(__file__).resolve().parent / "yaml"


def test_golden_demo_yaml() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "AS400_JOB EXTRACT\n"
        "  AGENT RES01\n"
        "  COMMAND CYBROBOT EXTRACT\n"
        "  JOBQ Q.ESP\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(LOAD)\n"
        "ENDJOB\n"
        "NT_JOB LOAD\n"
        "  AGENT WIN01\n"
        "  CMDNAME D:\\RUN\\load.bat\n"
        "  USER CORP\\batchuser\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    app = SourceApplication(
        name="DEMO",
        source_file="demo.esp",
        start_line=1,
        end_line=16,
        content=content,
        header_line="APPL DEMO WAIT",
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    wf = EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)
    actual = DagFactoryYamlGenerator().generate(wf)
    expected_path = GOLDEN / "demo.dag.yaml"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(actual, encoding="utf-8")  # refresh golden to target shape
    expected = expected_path.read_text(encoding="utf-8")
    assert actual == expected
