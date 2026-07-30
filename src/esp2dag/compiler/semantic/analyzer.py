"""ESP semantic analyzer — Phase 4.

Runs a list of focused ``SemanticRule`` checks over an ``ApplicationNode``.
Does not modify the AST and does not emit Airflow/YAML.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.context import SemanticResult
from esp2dag.compiler.semantic.base import SemanticRule
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.compiler.semantic.rules import default_rules
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity

logger = logging.getLogger(__name__)


class EspSemanticAnalyzer:
    """Composable semantic analyzer for one or many application ASTs."""

    def __init__(self, rules: list[SemanticRule] | None = None) -> None:
        self._rules = list(rules) if rules is not None else default_rules()

    @property
    def rules(self) -> list[SemanticRule]:
        """Configured rule plugins in execution order."""
        return list(self._rules)

    def analyze(self, ast: ApplicationNode) -> SemanticResult:
        """Validate a single application AST."""
        logger.info("Semantic analysis for application %s", ast.name)
        diagnostics: list[Diagnostic] = []
        for rule in self._rules:
            try:
                found = rule.check(ast)
            except Exception as exc:  # noqa: BLE001 - isolate rule failures
                logger.exception("Semantic rule %s failed", rule.name)
                found = [
                    diagnostic(
                        code=DiagnosticCode.E_SEM_INVALID_REF,
                        severity=Severity.ERROR,
                        message=f"Semantic rule '{rule.name}' crashed: {exc}",
                        span=ast.span,
                        application=ast.name,
                    )
                ]
            diagnostics.extend(found)
            logger.debug("Rule %s → %d diagnostic(s)", rule.name, len(found))

        logger.info(
            "Semantic analysis %s complete: %d diagnostic(s)",
            ast.name,
            len(diagnostics),
        )
        return SemanticResult(ast=ast, diagnostics=diagnostics)

    def analyze_batch(self, applications: list[ApplicationNode]) -> list[Diagnostic]:
        """Analyze many applications and add cross-application duplicate checks."""
        diagnostics: list[Diagnostic] = []
        for ast in applications:
            diagnostics.extend(self.analyze(ast).diagnostics)
        diagnostics.extend(self.cross_application_diagnostics(applications))
        return diagnostics

    def cross_application_diagnostics(
        self,
        applications: list[ApplicationNode],
    ) -> list[Diagnostic]:
        """Return diagnostics that require a multi-application view."""
        return self._duplicate_applications(applications)

    def _duplicate_applications(
        self,
        applications: list[ApplicationNode],
    ) -> list[Diagnostic]:
        by_name: dict[str, list[ApplicationNode]] = defaultdict(list)
        for ast in applications:
            by_name[ast.name.upper()].append(ast)

        diagnostics: list[Diagnostic] = []
        for _key, group in by_name.items():
            if len(group) < 2:
                continue
            first = group[0]
            for dup in group[1:]:
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_DUPLICATE_APP,
                        severity=Severity.ERROR,
                        message=(
                            f"Duplicate application name '{dup.name}' "
                            f"(also defined at line {first.span.start_line})."
                        ),
                        span=dup.span,
                        application=dup.name,
                        hint="Extraction kept both units; resolve before migration.",
                    )
                )
        return diagnostics
