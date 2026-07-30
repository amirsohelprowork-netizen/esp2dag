"""Deterministic task_id allocation with collision suffixes."""

from __future__ import annotations

from esp2dag.utils import sanitize_task_id


class TaskIdAllocator:
    """Allocate unique Airflow-safe task ids in declaration order."""

    def __init__(self) -> None:
        self._used: dict[str, int] = {}
        self._by_job: dict[str, str] = {}

    def allocate(self, job_name: str) -> str:
        """Return a stable unique task_id for ``job_name``."""
        if job_name in self._by_job:
            return self._by_job[job_name]

        base = sanitize_task_id(job_name)
        count = self._used.get(base, 0) + 1
        self._used[base] = count
        task_id = base if count == 1 else f"{base}_{count}"
        self._by_job[job_name] = task_id
        return task_id

    def resolve(self, job_name: str) -> str | None:
        """Lookup an already allocated id, trying bare name without (A) qualifier."""
        if job_name in self._by_job:
            return self._by_job[job_name]
        bare = job_name.split("(", 1)[0]
        return self._by_job.get(bare)

    def mapping(self) -> dict[str, str]:
        """Copy of job_name → task_id."""
        return dict(self._by_job)
