"""ESP lexer — Phase 2.

Tokenizes one ``SourceApplication`` into a deterministic ``list[Token]``.
Every token carries source file, absolute line, and column provenance.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from esp2dag.compiler.lexer.token import Token
from esp2dag.compiler.lexer.token_types import (
    JOB_TYPE_KEYWORDS,
    KEYWORD_MAP,
    TokenType,
)
from esp2dag.models.source import SourceApplication

logger = logging.getLogger(__name__)

# Word characters for ESP names / paths (excluding whitespace and hard punct).
_WORD_CHAR_RE = re.compile(r"[A-Za-z0-9_!.#@\\/$%*&?:]")


@dataclass
class LexerOptions:
    """Optional trivia emission (off by default for parser-friendly streams)."""

    include_comments: bool = False
    include_newlines: bool = False


class EspLexer:
    """Deterministic ESP lexer for one extracted application unit."""

    def __init__(self, options: LexerOptions | None = None) -> None:
        self._options = options or LexerOptions()

    def tokenize(self, application: SourceApplication) -> list[Token]:
        """Tokenize ``application.content`` with absolute source line numbers.

        Args:
            application: Unit from Phase 1 extraction.

        Returns:
            Token list ending with a single ``EOF`` token.
        """
        text = application.content.lstrip("\ufeff")
        scanner = _Scanner(
            text=text,
            source_file=application.source_file,
            base_line=application.start_line,
            options=self._options,
        )
        tokens = scanner.scan_all()
        logger.debug(
            "Lexed %s (%s:%s-%s) → %d tokens",
            application.name,
            application.source_file,
            application.start_line,
            application.end_line,
            len(tokens),
        )
        return tokens


class _Scanner:
    """Character scanner with line/column tracking."""

    def __init__(
        self,
        *,
        text: str,
        source_file: str,
        base_line: int,
        options: LexerOptions,
    ) -> None:
        self._text = text
        self._source_file = source_file
        self._base_line = base_line
        self._options = options
        self._i = 0
        self._line = 1  # 1-based within application content
        self._col = 1  # 1-based
        self._tokens: list[Token] = []

    def scan_all(self) -> list[Token]:
        """Scan the full text into tokens + EOF."""
        while not self._at_end():
            self._scan_token()
        self._emit(TokenType.EOF, "", self._line, self._col)
        return self._tokens

    def _scan_token(self) -> None:
        ch = self._peek()

        if ch in " \t":
            self._advance()
            return

        if ch == "\r":
            self._advance()
            if self._peek() == "\n":
                self._advance()
            self._newline()
            return

        if ch == "\n":
            self._advance()
            self._newline()
            return

        if ch == "/" and self._peek_at(1) == "*":
            self._scan_comment()
            return

        # Line continuation: '-' or '+' at EOL (optional spaces before newline).
        if ch in "-+" and self._is_line_continuation():
            self._consume_line_continuation()
            return

        if ch == "'":
            self._scan_string()
            return

        if ch.isdigit():
            self._scan_number()
            return

        if ch == "=":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.EQUALS, "=", line, col)
            return

        if ch == ",":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.COMMA, ",", line, col)
            return

        if ch == "(":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.LPAREN, "(", line, col)
            return

        if ch == ")":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.RPAREN, ")", line, col)
            return

        if ch == "+":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.PLUS, "+", line, col)
            return

        if ch == "-":
            line, col = self._line, self._col
            self._advance()
            self._emit(TokenType.MINUS, "-", line, col)
            return

        if self._is_word_start(ch):
            self._scan_word()
            return

        # Unknown single character — emit and continue (never abort).
        line, col = self._line, self._col
        self._advance()
        self._emit(TokenType.UNKNOWN, ch, line, col)

    def _scan_comment(self) -> None:
        line, col = self._line, self._col
        self._advance()  # /
        self._advance()  # *
        start = self._i
        closed = False
        while not self._at_end():
            if self._peek() == "*" and self._peek_at(1) == "/":
                value = self._text[start : self._i]
                self._advance()
                self._advance()
                closed = True
                if self._options.include_comments:
                    self._emit(TokenType.COMMENT, value, line, col)
                return
            if self._peek() in "\r\n":
                # Unclosed /* → end-of-line comment (matches extractor semantics).
                value = self._text[start : self._i]
                if self._options.include_comments:
                    self._emit(TokenType.COMMENT, value, line, col)
                return
            ch = self._advance()
            if ch == "\n":
                # Should not reach — handled above.
                self._line += 1
                self._col = 1
        value = self._text[start : self._i]
        if self._options.include_comments:
            self._emit(TokenType.COMMENT, value, line, col)
        _ = closed

    def _scan_string(self) -> None:
        line, col = self._line, self._col
        self._advance()  # opening '
        chars: list[str] = []
        while not self._at_end():
            ch = self._peek()
            if ch == "'":
                # ESP doubled quote '' → literal '
                if self._peek_at(1) == "'":
                    self._advance()
                    self._advance()
                    chars.append("'")
                    continue
                self._advance()
                break
            if ch in "\r\n":
                break
            chars.append(self._advance())
        self._emit(TokenType.STRING, "".join(chars), line, col)

    def _scan_number(self) -> None:
        line, col = self._line, self._col
        start = self._i
        while self._peek().isdigit():
            self._advance()
        # Decimal (e.g. 21.00) but not name-like 1.JOB
        if self._peek() == "." and self._peek_at(1).isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()
        value = self._text[start : self._i]
        # If followed by identifier chars (4PM, 001A), absorb as IDENTIFIER.
        if _WORD_CHAR_RE.match(self._peek()) and self._peek() not in ".":
            while _WORD_CHAR_RE.match(self._peek()):
                self._advance()
            value = self._text[start : self._i]
            self._emit_word(value, line, col)
            return
        self._emit(TokenType.NUMBER, value, line, col)

    def _scan_word(self) -> None:
        line, col = self._line, self._col
        start = self._i
        while not self._at_end() and _WORD_CHAR_RE.match(self._peek()):
            self._advance()
        value = self._text[start : self._i]
        self._emit_word(value, line, col)

    def _emit_word(self, value: str, line: int, col: int) -> None:
        upper = value.upper()
        if upper in KEYWORD_MAP:
            self._emit(KEYWORD_MAP[upper], value, line, col)
            return
        if upper in JOB_TYPE_KEYWORDS or _is_job_type_keyword(upper):
            self._emit(TokenType.JOB_TYPE, value, line, col)
            return
        self._emit(TokenType.IDENTIFIER, value, line, col)

    def _is_line_continuation(self) -> bool:
        """True when '-'/'+' is followed only by spaces then newline/EOF."""
        j = self._i + 1
        length = len(self._text)
        while j < length and self._text[j] in " \t":
            j += 1
        if j >= length:
            return True
        if self._text[j] == "\n":
            return True
        if self._text[j] == "\r":
            return True
        return False

    def _consume_line_continuation(self) -> None:
        self._advance()  # - or +
        while self._peek() in " \t":
            self._advance()
        if self._peek() == "\r":
            self._advance()
        if self._peek() == "\n":
            self._advance()
            self._line += 1
            self._col = 1

    def _newline(self) -> None:
        if self._options.include_newlines:
            # Column of newline is previous position; emit at start of new line concept.
            self._emit(TokenType.NEWLINE, "\n", self._line, 1)
        self._line += 1
        self._col = 1

    def _emit(self, token_type: TokenType, value: str, line: int, col: int) -> None:
        abs_line = self._base_line + line - 1
        self._tokens.append(
            Token(
                type=token_type,
                value=value,
                source_file=self._source_file,
                line=abs_line,
                column=col,
            )
        )

    def _at_end(self) -> bool:
        return self._i >= len(self._text)

    def _peek(self) -> str:
        if self._at_end():
            return ""
        return self._text[self._i]

    def _peek_at(self, offset: int) -> str:
        idx = self._i + offset
        if idx >= len(self._text):
            return ""
        return self._text[idx]

    def _advance(self) -> str:
        ch = self._text[self._i]
        self._i += 1
        if ch != "\n":
            self._col += 1
        return ch

    @staticmethod
    def _is_word_start(ch: str) -> bool:
        return bool(ch) and (
            ch.isalpha() or ch in "!.#_/\\" or ch == "$"
        )


def _is_job_type_keyword(upper: str) -> bool:
    """True for ESP workload object verbs like NT_JOB / SAP_JOB / AGENT_MONITOR."""
    if upper.endswith("_JOB"):
        return True
    if upper.endswith("_OBJECT"):
        return True
    return False
