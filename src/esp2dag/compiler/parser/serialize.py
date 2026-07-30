"""AST serialization helpers for CLI and golden tests."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode, JobNode


def application_summary(ast: ApplicationNode) -> dict[str, object]:
    """Compact deterministic summary of a parsed application."""
    return {
        "name": ast.name,
        "job_count": len(ast.jobs),
        "jobs": [_job_summary(job) for job in ast.jobs],
        "notifications": len(ast.notifications),
        "variables": len(ast.variables),
        "resources": len(ast.resources),
        "metadata_keys": sorted({m.key for m in ast.metadata}),
        "unsupported": [u.keyword for u in ast.unsupported],
    }


def _job_summary(job: JobNode) -> dict[str, object]:
    return {
        "name": job.name,
        "job_type": job.job_type,
        "releases": [d.predecessor for d in job.dependencies if d.dependency_type == "RELEASE"],
        "run": job.schedule.expression if job.schedule else None,
        "command": job.command.text if job.command else None,
        "resources": [r.name for r in job.resources],
        "agents": [m.value for m in job.metadata if m.key == "agent"],
        "unsupported": [u.keyword for u in job.unsupported],
    }
