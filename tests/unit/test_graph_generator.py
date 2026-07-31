"""Unit tests for Phase 9 dependency graph generators."""

from __future__ import annotations

import json

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder
from esp2dag.graph import WorkflowGraphGenerator
from esp2dag.models.config import GraphFormat
from esp2dag.models.source import SourceApplication
from esp2dag.models.workflow import Dependency


def _workflow(content: str, *, name: str = "DEMO"):
    app = SourceApplication(
        name=name,
        source_file="demo.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    return EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)


CONTENT = (
    "APPL DEMO WAIT\n"
    "NT_JOB EXTRACT\n"
    "  CMDNAME D:\\RUN\\extract.bat\n"
    "  AGENT WIN01\n"
    "  RUN DAILY\n"
    "  RELEASE ADD(LOAD)\n"
    "ENDJOB\n"
    "JOB LOAD\n"
    "  RUN DAILY\n"
    "ENDJOB\n"
)


def test_mermaid_graph_has_nodes_and_edge() -> None:
    wf = _workflow(CONTENT)
    text = WorkflowGraphGenerator().generate(wf, GraphFormat.MERMAID)
    assert "flowchart TD" in text
    assert "EXTRACT" in text
    assert "LOAD" in text
    assert "-->" in text


def test_json_graph_structure() -> None:
    wf = _workflow(CONTENT)
    payload = json.loads(WorkflowGraphGenerator().generate(wf, GraphFormat.JSON))
    assert payload["workflow_id"] == "demo"
    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
    assert payload["edges"][0]["from"] == "EXTRACT"
    assert payload["edges"][0]["to"] == "LOAD"
    assert "operator" in payload["nodes"][0]


def test_graphviz_dot() -> None:
    wf = _workflow(CONTENT)
    text = WorkflowGraphGenerator().generate(wf, GraphFormat.GRAPHVIZ)
    assert 'digraph "demo"' in text
    assert "EXTRACT" in text
    assert "->" in text


def test_graphs_surface_dangling_dependencies() -> None:
    wf = _workflow(CONTENT)
    wf = wf.model_copy(
        update={
            "dependencies": [
                Dependency(
                    upstream_task_id="MISSING",
                    downstream_task_id="LOAD",
                    condition="COMPLETE",
                )
            ]
        }
    )
    graph = WorkflowGraphGenerator()
    mermaid = graph.generate(wf, GraphFormat.MERMAID)
    assert "UNRESOLVED" in mermaid
    assert "COMPLETE" in mermaid
    payload = json.loads(graph.generate(wf, GraphFormat.JSON))
    assert any(node["id"] == "MISSING" and node["unresolved"] for node in payload["nodes"])
    assert payload["edges"][0]["resolved"] is False
    assert payload["edges"][0]["condition"] == "COMPLETE"
