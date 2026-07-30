"""ESP NOTWITH → Airflow pool exclusion groups.

``NOTWITH`` means jobs must not run concurrently. We model an undirected
exclusion graph (job → peers), take connected components, and assign one
shared Airflow pool name per component (slots=1 expected in Airflow).

Scenarios covered:

- Peers with totally different names (ALPHA / BETA / GAMMA)
- Many ``NOTWITH`` lines on one job
- Bidirectional or one-sided declarations
- Cross-application peers (same pool name across DAGs)
- Chains (A–B, B–C ⇒ A,B,C share one pool — conservative)
- Declared peer missing from compile set (still forms a group key)
"""

from __future__ import annotations

import logging
from collections import defaultdict

from esp2dag.models.workflow import Task, Workflow

logger = logging.getLogger(__name__)


def assign_notwith_pools(workflows: list[Workflow]) -> list[Workflow]:
    """Return workflows with ``notwith_pool`` / ``pool`` set for exclusion groups."""
    graph: dict[str, set[str]] = defaultdict(set)
    # Every job that declares NOTWITH or is named as a peer is a node.
    for wf in workflows:
        for task in wf.tasks:
            self_key = _norm(task.name)
            peers = _peer_list(task)
            if not peers:
                continue
            graph[self_key].add(self_key)
            for peer in peers:
                p = _norm(peer)
                graph[self_key].add(p)
                graph[p].add(self_key)
                graph[p].add(p)

    if not graph:
        return workflows

    components = _connected_components(graph)
    # Stable ordering of groups for nw_0001, nw_0002, ...
    components.sort(key=lambda c: sorted(c)[0])
    pool_by_job: dict[str, str] = {}
    for index, component in enumerate(components, start=1):
        # Skip empty; single phantom-only components still get a pool if
        # any real task maps into them (assigned below only for present tasks).
        if len(component) < 2:
            # Lone node with a self-loop only — still assign if it had peers
            # that collapsed oddly; normally peers make len>=2.
            continue
        pool = f"nw_{index:04d}"
        for job in component:
            pool_by_job[job] = pool

    # Singletons that listed peers which somehow didn't expand: still map.
    for node, neighbors in graph.items():
        if node not in pool_by_job and len(neighbors) >= 1:
            # Component of size 1 with declared edges to itself only
            pass

    # Re-build: any task whose name is in a multi-node component gets the pool.
    # Also size-1 components that had outbound peers to missing jobs: those
    # components have len>=2 because missing peer was added to the graph.
    assigned = 0
    updated: list[Workflow] = []
    for wf in workflows:
        new_tasks: list[Task] = []
        for task in wf.tasks:
            key = _norm(task.name)
            pool = pool_by_job.get(key)
            if pool is None:
                new_tasks.append(task)
                continue
            params = dict(task.params)
            params["notwith_pool"] = pool
            # NOTWITH mutex overrides RESOURCE-derived pool.
            new_tasks.append(task.model_copy(update={"params": params, "pool": pool}))
            assigned += 1
        updated.append(wf.model_copy(update={"tasks": new_tasks}))

    logger.info(
        "NOTWITH: %d exclusion group(s), %d task(s) assigned shared pools",
        len(components),
        assigned,
    )
    return updated


def _peer_list(task: Task) -> list[str]:
    raw = task.params.get("notwith_peers") or task.params.get("notwith") or ""
    return [p.strip() for p in raw.split(",") if p.strip()]


def _norm(name: str) -> str:
    return name.strip().upper()


def _connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []
    for start in sorted(graph.keys()):
        if start in seen:
            continue
        stack = [start]
        comp: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            comp.add(node)
            for nxt in graph.get(node, ()):
                if nxt not in seen:
                    stack.append(nxt)
        if comp:
            components.append(comp)
    return components
