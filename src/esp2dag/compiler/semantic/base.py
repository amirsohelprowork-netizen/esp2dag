"""Semantic rule protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.models.diagnostics import Diagnostic


@runtime_checkable
class SemanticRule(Protocol):
    """One focused semantic check over an application AST."""

    @property
    def name(self) -> str:
        """Stable rule name for logging."""

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        """Return diagnostics for this rule (never raises)."""
