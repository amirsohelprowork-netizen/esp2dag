"""Serialize tokens for golden tests and CLI output."""

from __future__ import annotations

from esp2dag.compiler.lexer.token import Token


def tokens_as_dicts(tokens: list[Token]) -> list[dict[str, object]]:
    """Convert tokens to JSON-serializable dicts (deterministic key order)."""
    return [
        {
            "type": token.type.value,
            "value": token.value,
            "line": token.line,
            "column": token.column,
        }
        for token in tokens
    ]


def tokens_compact(tokens: list[Token]) -> list[str]:
    """Compact ``TYPE:value`` forms for readable golden files (skips EOF)."""
    return [
        f"{token.type.value}:{token.value}"
        for token in tokens
        if token.type.value != "EOF"
    ]
