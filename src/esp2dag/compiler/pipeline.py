"""Compiler pipeline orchestrator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from esp2dag.models.config import (
    ArtifactKind,
    ArtifactRef,
    CompileRequest,
    CompileResult,
    CompileStatistics,
)
from esp2dag.models.diagnostics import Diagnostic, FailedUnit, Severity
from esp2dag.models.source import SourceFile
from esp2dag.models.workflow import Workflow
from esp2dag.compiler.workflow.notwith import assign_notwith_pools

if TYPE_CHECKING:
    from esp2dag.compiler.context import (
        AirflowGenerator,
        ApplicationExtractor,
        EventMerger,
        EventParser,
        GraphGenerator,
        Lexer,
        Parser,
        ReportGenerator,
        SemanticAnalyzer,
        WorkflowBuilder,
        WorkflowValidator,
        YamlGenerator,
    )

logger = logging.getLogger(__name__)


class CompilerPipeline:
    """Orchestrates the multi-stage ESP → DAG Factory compilation pipeline."""

    def __init__(
        self,
        *,
        extractor: ApplicationExtractor | None = None,
        lexer: Lexer | None = None,
        parser: Parser | None = None,
        analyzer: SemanticAnalyzer | None = None,
        workflow_builder: WorkflowBuilder | None = None,
        event_parser: EventParser | None = None,
        event_merger: EventMerger | None = None,
        workflow_validator: WorkflowValidator | None = None,
        yaml_generator: YamlGenerator | None = None,
        airflow_generator: AirflowGenerator | None = None,
        graph_generator: GraphGenerator | None = None,
        report_generator: ReportGenerator | None = None,
    ) -> None:
        self._extractor = extractor
        self._lexer = lexer
        self._parser = parser
        self._analyzer = analyzer
        self._workflow_builder = workflow_builder
        self._event_parser = event_parser
        self._event_merger = event_merger
        self._workflow_validator = workflow_validator
        self._yaml_generator = yaml_generator
        self._airflow_generator = airflow_generator
        self._graph_generator = graph_generator
        self._report_generator = report_generator

    def run(self, request: CompileRequest) -> CompileResult:
        """Execute the configured pipeline stages."""
        options = request.options
        logger.info(
            "Compile requested schedule=%s events=%s output=%s",
            request.schedule_path,
            request.events_path,
            request.output_dir,
        )

        if self._lexer is None or self._parser is None:
            raise RuntimeError("Lexer and parser are required for CompilerPipeline.run")
        if self._analyzer is None or self._workflow_builder is None:
            raise RuntimeError("Analyzer and workflow builder are required")

        from esp2dag.compiler.loader import load_applications

        request.output_dir.mkdir(parents=True, exist_ok=True)

        applications = load_applications(
            request.schedule_path,
            max_applications=options.max_applications,
        )
        workflows: list[Workflow] = []
        failures: list[FailedUnit] = []
        diagnostics: list[Diagnostic] = []

        for app_unit in applications:
            try:
                tokens = self._lexer.tokenize(app_unit)
                parse_result = self._parser.parse_with_diagnostics(tokens, app_unit)
                semantic = self._analyzer.analyze(parse_result.ast)
                unit_diags = list(parse_result.diagnostics) + list(semantic.diagnostics)
                diagnostics.extend(unit_diags)

                has_errors = any(
                    d.severity in {Severity.ERROR, Severity.FATAL} for d in unit_diags
                )
                if has_errors and options.skip_ir_on_semantic_error:
                    failures.append(
                        FailedUnit(
                            unit_id=app_unit.name,
                            stage="semantic",
                            diagnostics=unit_diags,
                        )
                    )
                    continue

                workflow = self._workflow_builder.build(parse_result.ast, unit_diags)
                workflows.append(workflow)
            except Exception as exc:  # noqa: BLE001 — per-app isolation
                if not options.continue_on_error:
                    raise
                logger.exception("Failed compiling application %s", app_unit.name)
                failures.append(
                    FailedUnit(
                        unit_id=app_unit.name,
                        stage="frontend",
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                    )
                )

        if request.events_path is not None and self._event_parser and self._event_merger:
            event_result = self._event_parser.parse_with_diagnostics(
                SourceFile(
                    path=request.events_path.resolve(),
                    content=request.events_path.read_text(
                        encoding="utf-8", errors="replace"
                    ),
                )
            )
            diagnostics.extend(event_result.diagnostics)
            merge_result = self._event_merger.merge_with_diagnostics(
                workflows, event_result.catalog
            )
            workflows = merge_result.workflows
            # Workflow diagnostics already contain the original per-app
            # diagnostics. Add only the new merger diagnostics once.
            diagnostics.extend(merge_result.diagnostics)

        # Global NOTWITH exclusion groups → shared Airflow pools (cross-DAG safe).
        workflows = assign_notwith_pools(workflows)

        if self._workflow_validator is not None:
            for wf in workflows:
                diagnostics.extend(self._workflow_validator.validate(wf))

        artifacts: list[ArtifactRef] = []

        if options.emit_yaml and self._yaml_generator is not None:
            yaml_dir = request.output_dir / "yaml"
            yaml_dir.mkdir(parents=True, exist_ok=True)
            for workflow in workflows:
                text = self._yaml_generator.generate(workflow)
                path = yaml_dir / f"{workflow.id}.yaml"
                path.write_text(text, encoding="utf-8")
                artifacts.append(
                    ArtifactRef(
                        kind=ArtifactKind.YAML,
                        path=path,
                        workflow_id=workflow.id,
                        format="yaml",
                    )
                )

        if options.emit_graph and self._graph_generator is not None:
            graph_dir = request.output_dir / "graphs"
            graph_dir.mkdir(parents=True, exist_ok=True)
            for workflow in workflows:
                for fmt in options.graph_formats:
                    text = self._graph_generator.generate(workflow, fmt)
                    ext = (
                        self._graph_generator.extension(fmt)
                        if hasattr(self._graph_generator, "extension")
                        else f".{fmt.value}"
                    )
                    path = graph_dir / f"{workflow.id}{ext}"
                    path.write_text(text, encoding="utf-8")
                    artifacts.append(
                        ArtifactRef(
                            kind=ArtifactKind.GRAPH,
                            path=path,
                            workflow_id=workflow.id,
                            format=fmt.value,
                        )
                    )

        if options.emit_airflow and self._airflow_generator is not None:
            raise NotImplementedError(
                "Phase 8 Airflow DAG generation is deferred; YAML is the deliverable."
            )

        statistics = _build_statistics(applications, workflows, failures, diagnostics)
        result = CompileResult(
            workflows=workflows,
            artifacts=artifacts,
            failures=failures,
            diagnostics=diagnostics,
            statistics=statistics,
        )

        if options.emit_reports and self._report_generator is not None:
            if hasattr(self._report_generator, "write"):
                report_artifacts = self._report_generator.write(
                    result, request.output_dir
                )
            else:
                report_artifacts = self._report_generator.generate(result)
            artifacts = list(artifacts) + list(report_artifacts)
            result = CompileResult(
                workflows=workflows,
                artifacts=artifacts,
                failures=failures,
                diagnostics=diagnostics,
                statistics=statistics,
            )

        return result


def _build_statistics(
    applications: list,
    workflows: list[Workflow],
    failures: list[FailedUnit],
    diagnostics: list[Diagnostic],
) -> CompileStatistics:
    return CompileStatistics(
        total_applications=len(applications),
        total_jobs=sum(len(w.tasks) for w in workflows),
        total_dependencies=sum(len(w.dependencies) for w in workflows),
        total_events=sum(len(w.events) for w in workflows),
        successful_conversions=len(workflows),
        failed_conversions=len(failures),
        unsupported_statements=sum(
            len(t.unsupported_features) for w in workflows for t in w.tasks
        ),
        warnings=sum(1 for d in diagnostics if d.severity == Severity.WARNING),
        errors=sum(
            1 for d in diagnostics if d.severity in {Severity.ERROR, Severity.FATAL}
        ),
        manual_review_required=sum(
            1
            for w in workflows
            if any(t.unsupported_features for t in w.tasks)
        ),
    )
