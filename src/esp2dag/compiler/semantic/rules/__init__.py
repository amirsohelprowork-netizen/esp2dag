"""Default semantic rule set."""

from __future__ import annotations

from esp2dag.compiler.semantic.base import SemanticRule
from esp2dag.compiler.semantic.rules.circular_dependencies import CircularDependencyRule
from esp2dag.compiler.semantic.rules.duplicate_jobs import DuplicateJobRule
from esp2dag.compiler.semantic.rules.empty_application import EmptyApplicationRule
from esp2dag.compiler.semantic.rules.invalid_references import InvalidReferenceRule
from esp2dag.compiler.semantic.rules.invalid_schedules import InvalidScheduleRule
from esp2dag.compiler.semantic.rules.missing_predecessors import MissingPredecessorRule
from esp2dag.compiler.semantic.rules.undefined_resources import UndefinedResourceRule
from esp2dag.compiler.semantic.rules.unsupported_syntax import UnsupportedSyntaxRule


def default_rules() -> list[SemanticRule]:
    """Ordered list of built-in semantic rules."""
    return [
        EmptyApplicationRule(),
        DuplicateJobRule(),
        MissingPredecessorRule(),
        CircularDependencyRule(),
        UndefinedResourceRule(),
        InvalidScheduleRule(),
        InvalidReferenceRule(),
        UnsupportedSyntaxRule(),
    ]
