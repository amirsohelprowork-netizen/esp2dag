"""Lexer token model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.compiler.lexer.token_types import TokenType


class Token(BaseModel):
    """A single lexeme with full source provenance."""

    model_config = ConfigDict(frozen=True)

    type: TokenType
    value: str
    source_file: str
    line: int = Field(ge=1)
    column: int = Field(ge=1)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.type}:{self.value!r}@{self.source_file}:{self.line}:{self.column}"
