"""Golden tests for Phase 2 lexer compact token streams."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.lexer.serialize import tokens_compact
from esp2dag.models.source import SourceApplication

GOLDEN = Path(__file__).resolve().parent / "lexer"


def test_golden_demo_snippet() -> None:
    content = (
        "APPL SAMPLEAPP WAIT\n"
        "INVOKE 'SYS.ESP.PROCLIB(#DISTRIB)'\n"
        "NOTIFY FAILURE ABEND ALERT(ALERT01)\n"
        "JOB LIE.UPSTREAM EXTERNAL APPLID(OTHERAPP)\n"
        "  RUN DAILY\n"
        "  RELEASE ADD(LIS.!ESPAPPL)\n"
        "ENDJOB\n"
        "NT_JOB WINSTEP\n"
        "  CMDNAME D:\\SCRIPTS\\WINSTEP.bat\n"
        "  USER CORP\\batchuser\n"
        "ENDJOB\n"
    )
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file="sampleapp.esp",
        start_line=1,
        end_line=12,
        content=content,
        header_line="APPL SAMPLEAPP WAIT",
    )
    actual = tokens_compact(EspLexer().tokenize(app))
    expected_path = GOLDEN / "demo_snippet.tokens.txt"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text("\n".join(actual) + "\n", encoding="utf-8")
    expected = expected_path.read_text(encoding="utf-8").splitlines()
    assert actual == expected
