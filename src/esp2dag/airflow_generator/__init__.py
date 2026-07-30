"""Optional Airflow DAG generator — Phase 8 (not yet implemented)."""

from __future__ import annotations

from esp2dag.models.workflow import Workflow


class AirflowDagGenerator:
    """Emit Airflow DAG Python modules from Workflow IR."""

    def generate(self, workflow: Workflow) -> str:
        """Generate a Python DAG module string."""
        raise NotImplementedError("Phase 8 Airflow Generator is not implemented yet.")
