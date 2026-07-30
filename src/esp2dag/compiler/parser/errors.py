"""Parser errors and result types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.lexer.token import Token
from esp2dag.models.diagnostics import Diagnostic


class ParseError(Exception):
    """Recoverable parse error used for synchronization."""

    def __init__(self, message: str, token: Token | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.token = token


class ParseResult(BaseModel):
    """AST plus diagnostics from Phase 3 parsing."""

    model_config = ConfigDict(frozen=True)

    ast: ApplicationNode
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """True when ERROR/FATAL diagnostics were produced."""
        return any(d.severity.value in {"ERROR", "FATAL"} for d in self.diagnostics)
