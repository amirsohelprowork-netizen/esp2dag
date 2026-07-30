"""Migration / validation / statistics reports — Phase 10."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.models.config import ArtifactKind, ArtifactRef, CompileResult
from esp2dag.reports.dependency import build_dependencies
from esp2dag.reports.migration import build_migration, migration_markdown
from esp2dag.reports.statistics import build_statistics, statistics_markdown
from esp2dag.reports.validation import build_validation, validation_markdown


class CompileReportGenerator:
    """Produce migration, validation, dependency, and statistics reports."""

    def generate(self, result: CompileResult) -> list[ArtifactRef]:
        """Generate report artifacts (in-memory content; caller may write to disk)."""
        stats = build_statistics(result)
        validation = build_validation(result)
        migration = build_migration(result)
        dependencies = build_dependencies(result)

        artifacts: list[ArtifactRef] = [
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="statistics.json",
                content=json.dumps(stats, indent=2, sort_keys=True) + "\n",
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="statistics.md",
                content=statistics_markdown(stats),
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="validation.json",
                content=json.dumps(validation, indent=2, sort_keys=True) + "\n",
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="validation.md",
                content=validation_markdown(validation),
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="migration.json",
                content=json.dumps(migration, indent=2, sort_keys=True) + "\n",
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="migration.md",
                content=migration_markdown(migration),
            ),
            ArtifactRef(
                kind=ArtifactKind.REPORT,
                format="dependencies.json",
                content=json.dumps(dependencies, indent=2, sort_keys=True) + "\n",
            ),
        ]
        return artifacts

    def write(self, result: CompileResult, output_dir: Path) -> list[ArtifactRef]:
        """Generate reports and write them under ``output_dir/reports``."""
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        written: list[ArtifactRef] = []
        for artifact in self.generate(result):
            filename = artifact.format or "report.txt"
            path = reports_dir / filename
            path.write_text(artifact.content or "", encoding="utf-8")
            written.append(
                ArtifactRef(
                    kind=ArtifactKind.REPORT,
                    path=path,
                    format=artifact.format,
                    content=None,
                )
            )
        return written


__all__ = ["CompileReportGenerator"]
