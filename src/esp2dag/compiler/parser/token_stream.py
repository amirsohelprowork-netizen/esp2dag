"""Token cursor for the recursive descent parser."""

from __future__ import annotations

from esp2dag.compiler.lexer.token import Token
from esp2dag.compiler.lexer.token_types import TokenType
from esp2dag.compiler.parser.errors import ParseError


class TokenStream:
    """Indexed view over a token list with lookahead helpers."""

    def __init__(self, tokens: list[Token]) -> None:
        if not tokens:
            raise ValueError("TokenStream requires at least an EOF token")
        self._tokens = tokens
        self._i = 0

    @property
    def current(self) -> Token:
        """Token at the cursor (never advances past EOF)."""
        return self._tokens[self._i]

    def peek(self, offset: int = 0) -> Token:
        """Lookahead token; clamps within the token list."""
        idx = max(0, min(self._i + offset, len(self._tokens) - 1))
        return self._tokens[idx]

    def check(self, *types: TokenType) -> bool:
        """True if current token matches any of ``types``."""
        return self.current.type in types

    def check_value(self, *values: str) -> bool:
        """True if current IDENTIFIER/keyword value matches (case-insensitive)."""
        return self.current.value.upper() in {v.upper() for v in values}

    def match(self, *types: TokenType) -> Token | None:
        """Consume and return current token if type matches."""
        if self.check(*types):
            return self.advance()
        return None

    def advance(self) -> Token:
        """Consume current token and return it."""
        token = self.current
        if token.type != TokenType.EOF:
            self._i += 1
        return token

    def expect(self, *types: TokenType, message: str | None = None) -> Token:
        """Consume a token of the expected type or raise ``ParseError``."""
        if self.check(*types):
            return self.advance()
        expected = ", ".join(t.value for t in types)
        msg = message or f"Expected {expected}, found {self.current.type.value}"
        raise ParseError(msg, self.current)

    def at_end(self) -> bool:
        """True when cursor is on EOF."""
        return self.current.type == TokenType.EOF

    def consume_until(self, *types: TokenType) -> list[Token]:
        """Advance until current is one of ``types`` or EOF; return skipped tokens."""
        skipped: list[Token] = []
        while not self.at_end() and not self.check(*types):
            skipped.append(self.advance())
        return skipped
