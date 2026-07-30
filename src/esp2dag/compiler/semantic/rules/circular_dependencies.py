"""Detect circular dependencies within an application."""

from __future__ import annotations

from collections import defaultdict

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic, job_index
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity


class CircularDependencyRule:
    """Find cycles in the intra-application dependency graph."""

    @property
    def name(self) -> str:
        return "circular_dependencies"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        jobs = job_index(ast)
        graph: dict[str, set[str]] = defaultdict(set)

        for job in ast.jobs:
            for dep in job.dependencies:
                target = dep.predecessor.split("(", 1)[0]
                if target not in jobs:
                    continue
                kind = (dep.dependency_type or "AFTER").upper()
                if kind == "RELEASE":
                    # job releases target ⇒ edge job → target
                    graph[job.name].add(target)
                else:
                    # target precedes job ⇒ edge target → job
                    graph[target].add(job.name)

        diagnostics: list[Diagnostic] = []
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []
        reported: set[tuple[str, ...]] = set()

        def dfs(node: str) -> None:
            visiting.add(node)
            stack.append(node)
            for nxt in sorted(graph.get(node, ())):
                if nxt in visiting:
                    cycle_start = stack.index(nxt)
                    cycle = tuple(stack[cycle_start:] + [nxt])
                    canon = _canonicalize_cycle(cycle)
                    if canon not in reported:
                        reported.add(canon)
                        job = jobs[node]
                        diagnostics.append(
                            diagnostic(
                                code=DiagnosticCode.E_SEM_CIRCULAR_DEP,
                                severity=Severity.ERROR,
                                message=(
                                    f"Circular dependency detected in '{ast.name}': "
                                    + " → ".join(cycle)
                                ),
                                span=job.span,
                                application=ast.name,
                                job=node,
                                hint="Break the cycle by adjusting RELEASE/AFTER relationships.",
                            )
                        )
                elif nxt not in visited:
                    dfs(nxt)
            stack.pop()
            visiting.remove(node)
            visited.add(node)

        for name in sorted(jobs):
            if name not in visited:
                dfs(name)
        return diagnostics


def _canonicalize_cycle(cycle: tuple[str, ...]) -> tuple[str, ...]:
    """Rotate cycle so the lexicographically smallest edge-start comes first."""
    if len(cycle) < 2:
        return cycle
    body = list(cycle[:-1])  # last duplicates first
    if not body:
        return cycle
    min_i = min(range(len(body)), key=lambda i: body[i])
    rotated = body[min_i:] + body[:min_i]
    return tuple(rotated + [rotated[0]])
