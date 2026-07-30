"""Golden tests for Phase 5 Workflow IR summaries."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder, workflow_summary
from esp2dag.models.source import SourceApplication

GOLDEN = Path(__file__).resolve().parent / "workflow"


def test_golden_simple_workflow_summary() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "TAG DEMO\n"
        "NT_JOB EXTRACT\n"
        "  CMDNAME D:\\RUN\\extract.bat\n"
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
    actual = workflow_summary(wf)
    expected_path = GOLDEN / "demo.summary.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    if not expected_path.exists():
        expected_path.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected
