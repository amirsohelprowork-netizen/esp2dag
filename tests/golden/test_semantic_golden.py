"""Golden tests for Phase 4 semantic diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.models.source import SourceApplication

GOLDEN = Path(__file__).resolve().parent / "semantic"


def test_golden_cycle_diagnostics() -> None:
    content = (
        "APPL CYCLE\n"
        "JOB A\n  RUN DAILY\n  RELEASE ADD(B)\nENDJOB\n"
        "JOB B\n  RUN DAILY\n  RELEASE ADD(A)\nENDJOB\n"
    )
    app = SourceApplication(
        name="CYCLE",
        source_file="cycle.esp",
        start_line=1,
        end_line=8,
        content=content,
        header_line="APPL CYCLE",
    )
    result = EspSemanticAnalyzer().analyze(
        EspParser().parse(EspLexer().tokenize(app), app)
    )
    actual = sorted({d.code for d in result.diagnostics})
    expected_path = GOLDEN / "cycle.codes.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    if not expected_path.exists():
        expected_path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected
