"""Compiler configuration and request/result aggregates."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from esp2dag.models.diagnostics import Diagnostic, FailedUnit
from esp2dag.models.workflow import Workflow


class GraphFormat(StrEnum):
    """Supported dependency graph output formats."""

    MERMAID = "mermaid"
    GRAPHVIZ = "graphviz"
    JSON = "json"


class ArtifactKind(StrEnum):
    """Kinds of files emitted by the compiler."""

    YAML = "yaml"
    AIRFLOW_DAG = "airflow_dag"
    GRAPH = "graph"
    REPORT = "report"
    EXTRACT = "extract"


class CompilerConfig(BaseModel):
    """Feature flags and generation options for a compile run."""

    model_config = ConfigDict(frozen=True)

    emit_yaml: bool = True
    emit_airflow: bool = False
    emit_graph: bool = True
    emit_reports: bool = True
    graph_formats: list[GraphFormat] = Field(
        default_factory=lambda: [GraphFormat.MERMAID, GraphFormat.JSON]
    )
    fail_on_warnings: bool = False
    continue_on_error: bool = True
    skip_ir_on_semantic_error: bool = False
    task_id_style: str = "sanitize"
    dag_factory_profile: str = "default"
    conversion_version: str = "0.1.0"
    max_applications: int = 0  # 0 = all



class CompileRequest(BaseModel):
    """Inputs for CompilerPipeline.run."""

    model_config = ConfigDict(frozen=True)

    schedule_path: Path
    events_path: Path | None = None
    output_dir: Path
    options: CompilerConfig = Field(default_factory=CompilerConfig)


class ArtifactRef(BaseModel):
    """Reference to an emitted artifact on disk or in memory."""

    model_config = ConfigDict(frozen=True)

    kind: ArtifactKind
    path: Path | None = None
    workflow_id: str | None = None
    format: str | None = None
    content: str | None = None


class CompileStatistics(BaseModel):
    """Aggregate counters for reports."""

    model_config = ConfigDict(frozen=True)

    total_applications: int = 0
    total_jobs: int = 0
    total_dependencies: int = 0
    total_events: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    unsupported_statements: int = 0
    warnings: int = 0
    errors: int = 0
    manual_review_required: int = 0


class CompileResult(BaseModel):
    """Full outcome of a pipeline run."""

    model_config = ConfigDict(frozen=True)

    workflows: list[Workflow] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    failures: list[FailedUnit] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    statistics: CompileStatistics = Field(default_factory=CompileStatistics)

    @property
    def ok(self) -> bool:
        """True when no ERROR/FATAL diagnostics and no failed units."""
        if self.failures:
            return False
        return not any(d.severity.value in {"ERROR", "FATAL"} for d in self.diagnostics)
