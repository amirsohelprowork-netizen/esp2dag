"""Golden tests for Phase 3 parser summaries."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser, application_summary
from esp2dag.models.source import SourceApplication

GOLDEN = Path(__file__).resolve().parent / "parser"


def test_golden_demo_snippet_summary() -> None:
    content = (
        "APPL SAMPLEAPP WAIT\n"
        "INVOKE 'SYS.ESP.PROCLIB(#DISTRIB)'\n"
        "NOTIFY FAILURE ABEND ALERT(ALERT01)\n"
        "TAG DEMOTAG\n"
        "JOB LIE.UPSTREAM EXTERNAL APPLID(OTHERAPP)\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(LIS.!ESPAPPL)\n"
        "ENDJOB\n"
        "NT_JOB WINSTEP\n"
        "  AGENT AGENT02\n"
        "  CMDNAME D:\\SCRIPTS\\WINSTEP.bat\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(NEXTSTEP)\n"
        "ENDJOB\n"
    )
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file="sampleapp.esp",
        start_line=1,
        end_line=14,
        content=content,
        header_line="APPL SAMPLEAPP WAIT",
    )
    result = EspParser().parse_with_diagnostics(EspLexer().tokenize(app), app)
    actual = application_summary(result.ast)
    expected_path = GOLDEN / "demo_snippet.summary.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(
        json.dumps(actual, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected
