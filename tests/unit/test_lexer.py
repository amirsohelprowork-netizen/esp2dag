"""Unit tests for Phase 2 ESP lexer."""

from __future__ import annotations

from pathlib import Path

from esp2dag.compiler.lexer import EspLexer, LexerOptions, TokenType
from esp2dag.compiler.lexer.serialize import tokens_compact
from esp2dag.extractor import ApplicationExtractor
from esp2dag.models.source import SourceApplication, SourceFile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schedules"
DEMO_APP = FIXTURES / "demo_app.esp"


def _app(content: str, *, start_line: int = 1, name: str = "T") -> SourceApplication:
    return SourceApplication(
        name=name,
        source_file="test.esp",
        start_line=start_line,
        end_line=start_line + max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )


def test_tokenize_simple_appl_and_job() -> None:
    content = "APPL APP_A WAIT\nJOB JOB1\n  RUN DAILY\nENDJOB\n"
    tokens = EspLexer().tokenize(_app(content))
    compact = tokens_compact(tokens)
    assert compact[0] == "APPL:APPL"
    assert compact[1] == "IDENTIFIER:APP_A"
    assert compact[2] == "WAIT:WAIT"
    assert compact[3] == "JOB:JOB"
    assert compact[4] == "IDENTIFIER:JOB1"
    assert compact[5] == "RUN:RUN"
    assert compact[6] == "IDENTIFIER:DAILY"
    assert compact[7] == "ENDJOB:ENDJOB"
    assert tokens[-1].type == TokenType.EOF


def test_absolute_line_numbers_use_application_base() -> None:
    content = "APPL X\nJOB Y\nENDJOB\n"
    tokens = EspLexer().tokenize(_app(content, start_line=100))
    assert tokens[0].line == 100  # APPL
    assert tokens[2].line == 101  # JOB
    assert tokens[4].line == 102  # ENDJOB


def test_string_and_invoke() -> None:
    content = "INVOKE 'SYS.ESP.PROCLIB(#DISTRIB)'\n"
    tokens = EspLexer().tokenize(_app(content))
    assert tokens[0].type == TokenType.INVOKE
    assert tokens[1].type == TokenType.STRING
    assert tokens[1].value == "SYS.ESP.PROCLIB(#DISTRIB)"


def test_doubled_quotes_in_string() -> None:
    tokens = EspLexer().tokenize(_app("SETVAR X='IT''S'\n"))
    strings = [t for t in tokens if t.type == TokenType.STRING]
    assert strings[0].value == "IT'S"


def test_release_add_parens() -> None:
    content = "RELEASE ADD(LIS.!ESPAPPL)\n"
    tokens = EspLexer().tokenize(_app(content))
    compact = tokens_compact(tokens)
    assert compact == [
        "RELEASE:RELEASE",
        "ADD:ADD",
        "LPAREN:(",
        "IDENTIFIER:LIS.!ESPAPPL",
        "RPAREN:)",
    ]


def test_resource_add_number_and_name() -> None:
    content = "RESOURCE ADD(1,RES01)\n"
    compact = tokens_compact(EspLexer().tokenize(_app(content)))
    assert compact == [
        "RESOURCE:RESOURCE",
        "ADD:ADD",
        "LPAREN:(",
        "NUMBER:1",
        "COMMA:,",
        "IDENTIFIER:RES01",
        "RPAREN:)",
    ]


def test_job_type_keywords() -> None:
    content = "NT_JOB FOO\nAS400_JOB BAR\nAGENT_MONITOR BAZ\nENDJOB\n"
    types = [t.type for t in EspLexer().tokenize(_app(content)) if t.type != TokenType.EOF]
    assert types[0] == TokenType.JOB_TYPE
    assert types[2] == TokenType.JOB_TYPE
    assert types[4] == TokenType.JOB_TYPE


def test_windows_path_and_user_backslash() -> None:
    content = "CMDNAME D:\\SCRIPTS\\WINSTEP.bat\nUSER CORP\\batchuser\n"
    tokens = EspLexer().tokenize(_app(content))
    values = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
    assert "D:\\SCRIPTS\\WINSTEP.bat" in values
    assert "CORP\\batchuser" in values


def test_comments_skipped_by_default() -> None:
    content = "APPL A\n/* comment */\nJOB B\n/* eol comment\nENDJOB\n"
    compact = tokens_compact(EspLexer().tokenize(_app(content)))
    assert all(not c.startswith("COMMENT:") for c in compact)
    assert compact == [
        "APPL:APPL",
        "IDENTIFIER:A",
        "JOB:JOB",
        "IDENTIFIER:B",
        "ENDJOB:ENDJOB",
    ]


def test_comments_emitted_when_requested() -> None:
    content = "APPL A /* c */\n"
    tokens = EspLexer(LexerOptions(include_comments=True)).tokenize(_app(content))
    assert any(t.type == TokenType.COMMENT for t in tokens)


def test_line_continuation_hyphen() -> None:
    content = "IF A AND -\n    B THEN\n"
    compact = tokens_compact(EspLexer().tokenize(_app(content)))
    assert compact == [
        "IF:IF",
        "IDENTIFIER:A",
        "IDENTIFIER:AND",
        "IDENTIFIER:B",
        "THEN:THEN",
    ]
    assert "MINUS:-" not in compact


def test_decimal_number() -> None:
    tokens = EspLexer().tokenize(_app("DELAYSUB 21.00\n"))
    assert any(t.type == TokenType.NUMBER and t.value == "21.00" for t in tokens)


def test_number_suffixed_becomes_identifier() -> None:
    tokens = EspLexer().tokenize(_app("DUEOUT EXEC 4PM\n"))
    assert any(t.type == TokenType.IDENTIFIER and t.value == "4PM" for t in tokens)


def test_unknown_character_does_not_abort() -> None:
    tokens = EspLexer().tokenize(_app("JOB A\n  ~\nENDJOB\n"))
    assert any(t.type == TokenType.UNKNOWN and t.value == "~" for t in tokens)
    assert tokens[-1].type == TokenType.EOF


def test_deterministic_twice() -> None:
    content = "APPL A WAIT\nNOTIFY FAILURE ABEND ALERT(REMD)\n"
    a = tokens_compact(EspLexer().tokenize(_app(content)))
    b = tokens_compact(EspLexer().tokenize(_app(content)))
    assert a == b


def test_lex_fixture_sample_multi_app_unit() -> None:
    source = SourceFile(
        path=FIXTURES / "sample_multi_app.esp",
        content=(FIXTURES / "sample_multi_app.esp").read_text(encoding="utf-8"),
    )
    apps = ApplicationExtractor().extract(source).applications
    tokens = EspLexer().tokenize(apps[0])
    compact = tokens_compact(tokens)
    assert compact[0].startswith("APPL:")
    assert "JOB:JOB" in compact
    assert tokens[0].line == apps[0].start_line


def test_lex_demo_app_fixture() -> None:
    text = DEMO_APP.read_text(encoding="utf-8")
    app = SourceApplication(
        name="SAMPLEAPP",
        source_file=str(DEMO_APP),
        start_line=1,
        end_line=text.count("\n") + 1,
        content=text,
        header_line="APPL SAMPLEAPP WAIT",
    )
    tokens = EspLexer().tokenize(app)
    compact = tokens_compact(tokens)
    assert compact[0] == "APPL:APPL"
    assert "JOB_TYPE:NT_JOB" in compact or "JOB_TYPE:AS400_JOB" in compact or "JOB:JOB" in compact
    assert "ENDJOB:ENDJOB" in compact
    assert tokens[0].line == app.start_line
