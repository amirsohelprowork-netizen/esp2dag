"""Stage protocols and shared compile context.

Concrete stage implementations are added one phase at a time after approval.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.lexer.token import Token
from esp2dag.models.config import ArtifactRef, CompileRequest, CompileResult, GraphFormat
from esp2dag.models.diagnostics import Diagnostic
from esp2dag.models.events import EventCatalog
from esp2dag.models.source import SourceApplication, SourceFile
from esp2dag.models.workflow import Workflow


class ExtractResult(BaseModel):
    """Output of the application extractor."""

    model_config = ConfigDict(frozen=True)

    applications: list[SourceApplication] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class SemanticResult(BaseModel):
    """Output of semantic analysis for one application AST."""

    model_config = ConfigDict(frozen=True)

    ast: ApplicationNode
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """True if any ERROR/FATAL diagnostics were produced."""
        return any(d.severity.value in {"ERROR", "FATAL"} for d in self.diagnostics)


@runtime_checkable
class ApplicationExtractor(Protocol):
    """Phase 1: split schedule file into application units."""

    def extract(self, source: SourceFile) -> ExtractResult: ...


@runtime_checkable
class Lexer(Protocol):
    """Phase 2: tokenize one application."""

    def tokenize(self, application: SourceApplication) -> list[Token]: ...


@runtime_checkable
class Parser(Protocol):
    """Phase 3: tokens → AST."""

    def parse(
        self,
        tokens: list[Token],
        application: SourceApplication,
    ) -> ApplicationNode: ...


@runtime_checkable
class SemanticAnalyzer(Protocol):
    """Phase 4: validate AST semantics."""

    def analyze(self, ast: ApplicationNode) -> SemanticResult: ...


@runtime_checkable
class WorkflowBuilder(Protocol):
    """Phase 5: AST → Workflow IR."""

    def build(
        self,
        ast: ApplicationNode,
        diagnostics: list[Diagnostic],
    ) -> Workflow: ...


@runtime_checkable
class EventParser(Protocol):
    """Phase 6a: parse events file."""

    def parse(self, source: SourceFile) -> EventCatalog: ...


@runtime_checkable
class EventMerger(Protocol):
    """Phase 6b: enrich workflows with events."""

    def merge(
        self,
        workflows: list[Workflow],
        catalog: EventCatalog,
    ) -> list[Workflow]: ...


@runtime_checkable
class WorkflowValidator(Protocol):
    """Validate IR before generation."""

    def validate(self, workflow: Workflow) -> list[Diagnostic]: ...


@runtime_checkable
class YamlGenerator(Protocol):
    """Phase 7: Workflow → DAG Factory YAML."""

    def generate(self, workflow: Workflow) -> str: ...


@runtime_checkable
class AirflowGenerator(Protocol):
    """Phase 8: Workflow → Airflow DAG Python."""

    def generate(self, workflow: Workflow) -> str: ...


@runtime_checkable
class GraphGenerator(Protocol):
    """Phase 9: Workflow → graph artifact."""

    def generate(self, workflow: Workflow, fmt: GraphFormat) -> str: ...


@runtime_checkable
class ReportGenerator(Protocol):
    """Phase 10: CompileResult → reports."""

    def generate(self, result: CompileResult) -> list[ArtifactRef]: ...


class CompileContext(BaseModel):
    """Mutable-ish bag of shared state for a single pipeline run.

    Kept as a Pydantic model with non-frozen config so the orchestrator can
    accumulate diagnostics without threading dozens of parameters.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    request: CompileRequest
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    def add_diagnostics(self, items: list[Diagnostic]) -> None:
        """Append diagnostics in encounter order."""
        self.diagnostics.extend(items)
