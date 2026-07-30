"""Composition root — wire concrete compiler stages."""

from __future__ import annotations

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.pipeline import CompilerPipeline
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.event_parser import EspEventMerger, EspEventParser
from esp2dag.extractor import ApplicationExtractor
from esp2dag.graph import WorkflowGraphGenerator
from esp2dag.reports import CompileReportGenerator
from esp2dag.validators import WorkflowValidator
from esp2dag.yaml_generator import DagFactoryYamlGenerator


def build_pipeline(*, profile: str = "default") -> CompilerPipeline:
    """Construct a fully wired CompilerPipeline."""
    return CompilerPipeline(
        extractor=ApplicationExtractor(),
        lexer=EspLexer(),
        parser=EspParser(),
        analyzer=EspSemanticAnalyzer(),
        workflow_builder=EspWorkflowBuilder(),
        event_parser=EspEventParser(),
        event_merger=EspEventMerger(),
        workflow_validator=WorkflowValidator(),
        yaml_generator=DagFactoryYamlGenerator(profile=profile),
        graph_generator=WorkflowGraphGenerator(),
        report_generator=CompileReportGenerator(),
    )
