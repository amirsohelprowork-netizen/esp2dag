"""Golden tests for Phase 9 Mermaid graphs."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.graph import WorkflowGraphGenerator
from esp2dag.models.config import GraphFormat
from esp2dag.models.source import SourceApplication

GOLDEN = Path(__file__).resolve().parent / "graph"


def test_golden_demo_mermaid() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB EXTRACT\n"
        "  CMDNAME D:\\RUN\\extract.bat\n"
        "  AGENT WIN01\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(LOAD)\n"
        "ENDJOB\n"
        "JOB LOAD\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    app = SourceApplication(
        name="DEMO",
        source_file="demo.esp",
        start_line=1,
        end_line=12,
        content=content,
        header_line="APPL DEMO WAIT",
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    wf = EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)
    actual = WorkflowGraphGenerator().generate(wf, GraphFormat.MERMAID)
    expected_path = GOLDEN / "demo.mmd"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(actual, encoding="utf-8")
    assert actual == expected_path.read_text(encoding="utf-8")
