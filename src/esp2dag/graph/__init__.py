"""Dependency graph generators — Phase 9."""

from __future__ import annotations

from esp2dag.graph.graphviz import render_graphviz
from esp2dag.graph.json_graph import render_json_graph
from esp2dag.graph.mermaid import render_mermaid
from esp2dag.models.config import GraphFormat
from esp2dag.models.workflow import Workflow

_EXTENSIONS = {
    GraphFormat.MERMAID: ".mmd",
    GraphFormat.JSON: ".json",
    GraphFormat.GRAPHVIZ: ".dot",
}


class WorkflowGraphGenerator:
    """Generate Mermaid / Graphviz / JSON graphs from Workflow IR."""

    def generate(self, workflow: Workflow, fmt: GraphFormat) -> str:
        """Render a dependency graph in the requested format."""
        if fmt == GraphFormat.MERMAID:
            return render_mermaid(workflow)
        if fmt == GraphFormat.JSON:
            return render_json_graph(workflow)
        if fmt == GraphFormat.GRAPHVIZ:
            return render_graphviz(workflow)
        raise ValueError(f"Unsupported graph format: {fmt}")

    def extension(self, fmt: GraphFormat) -> str:
        """Return the file extension for a graph format."""
        return _EXTENSIONS[fmt]


__all__ = ["WorkflowGraphGenerator"]
