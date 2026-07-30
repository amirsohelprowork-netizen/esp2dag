"""Lexer token type enumeration."""

from __future__ import annotations

from enum import StrEnum


class TokenType(StrEnum):
    """ESP lexical token categories.

    Structural keywords are distinct types. Unknown words become IDENTIFIER
    so the parser can accept ESP dialect vocabulary without lexer churn.
    """

    # Application structure
    APPL = "APPL"
    APPLICATION = "APPLICATION"
    ENDAPPL = "ENDAPPL"

    # Job structure
    JOB = "JOB"
    JOB_TYPE = "JOB_TYPE"  # NT_JOB, AS400_JOB, AGENT_MONITOR, ...
    ENDJOB = "ENDJOB"
    DATA_OBJECT = "DATA_OBJECT"

    # Common statement keywords
    INVOKE = "INVOKE"
    NOTIFY = "NOTIFY"
    AMNOTIFY = "AMNOTIFY"
    RUN = "RUN"
    AFTER = "AFTER"
    RELEASE = "RELEASE"
    RESOURCE = "RESOURCE"
    SCHEDULE = "SCHEDULE"
    CALENDAR = "CALENDAR"
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    DO = "DO"
    ENDDO = "ENDDO"
    EXITCODE = "EXITCODE"
    RETRY = "RETRY"
    EVENT = "EVENT"
    LINK = "LINK"
    PROCESS = "PROCESS"
    EXTERNAL = "EXTERNAL"
    APPLID = "APPLID"
    AGENT = "AGENT"
    COMMAND = "COMMAND"
    CMDNAME = "CMDNAME"
    SCRIPTNAME = "SCRIPTNAME"
    ARGS = "ARGS"
    USER = "USER"
    TAG = "TAG"
    NOTWITH = "NOTWITH"
    DELAYSUB = "DELAYSUB"
    EARLYSUB = "EARLYSUB"
    SETVAR = "SETVAR"
    OPTIONS = "OPTIONS"
    ADD = "ADD"
    CCCHK = "CCCHK"
    DUEOUT = "DUEOUT"
    JOBQ = "JOBQ"
    WAIT = "WAIT"

    # Literals / symbols
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    EQUALS = "EQUALS"
    COMMA = "COMMA"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    PLUS = "PLUS"
    MINUS = "MINUS"
    DOT = "DOT"

    # Trivia / stream control
    COMMENT = "COMMENT"
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    UNKNOWN = "UNKNOWN"


# Uppercase keyword → token type (JOB_TYPE handled separately via suffix rules).
KEYWORD_MAP: dict[str, TokenType] = {
    "APPL": TokenType.APPL,
    "APPLICATION": TokenType.APPLICATION,
    "ENDAPPL": TokenType.ENDAPPL,
    "JOB": TokenType.JOB,
    "ENDJOB": TokenType.ENDJOB,
    "DATA_OBJECT": TokenType.DATA_OBJECT,
    "INVOKE": TokenType.INVOKE,
    "NOTIFY": TokenType.NOTIFY,
    "AMNOTIFY": TokenType.AMNOTIFY,
    "RUN": TokenType.RUN,
    "AFTER": TokenType.AFTER,
    "RELEASE": TokenType.RELEASE,
    "RESOURCE": TokenType.RESOURCE,
    "SCHEDULE": TokenType.SCHEDULE,
    "CALENDAR": TokenType.CALENDAR,
    "IF": TokenType.IF,
    "THEN": TokenType.THEN,
    "ELSE": TokenType.ELSE,
    "DO": TokenType.DO,
    "ENDDO": TokenType.ENDDO,
    "EXITCODE": TokenType.EXITCODE,
    "RETRY": TokenType.RETRY,
    "EVENT": TokenType.EVENT,
    "LINK": TokenType.LINK,
    "PROCESS": TokenType.PROCESS,
    "EXTERNAL": TokenType.EXTERNAL,
    "APPLID": TokenType.APPLID,
    "AGENT": TokenType.AGENT,
    "COMMAND": TokenType.COMMAND,
    "CMDNAME": TokenType.CMDNAME,
    "SCRIPTNAME": TokenType.SCRIPTNAME,
    "ARGS": TokenType.ARGS,
    "USER": TokenType.USER,
    "TAG": TokenType.TAG,
    "NOTWITH": TokenType.NOTWITH,
    "DELAYSUB": TokenType.DELAYSUB,
    "EARLYSUB": TokenType.EARLYSUB,
    "SETVAR": TokenType.SETVAR,
    "OPTIONS": TokenType.OPTIONS,
    "ADD": TokenType.ADD,
    "CCCHK": TokenType.CCCHK,
    "DUEOUT": TokenType.DUEOUT,
    "JOBQ": TokenType.JOBQ,
    "WAIT": TokenType.WAIT,
}

# Explicit non-JOB_* workload object kinds → JOB_TYPE.
JOB_TYPE_KEYWORDS: frozenset[str] = frozenset(
    {
        "AGENT_MONITOR",
        "APPLEND",
        "DSTRIG",
        "FILE_TRIGGER",
        "LINK_JOB",
        "TASK",
    }
)
