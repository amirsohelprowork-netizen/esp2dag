"""Helpers for writing Phase 1 extraction artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from esp2dag.compiler.context import ExtractResult
from esp2dag.models.source import SourceApplication
from esp2dag.utils import canonical_newline

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def application_filename(app: SourceApplication) -> str:
    """Deterministic filename for an extracted application unit."""
    safe = _UNSAFE_FILENAME.sub("_", app.name).strip("._") or "app"
    return f"{safe}__L{app.start_line}.esp"


def write_extract_artifacts(result: ExtractResult, output_dir: Path) -> list[Path]:
    """Write per-application slices and a manifest.json.

    Returns:
        Paths of written files (manifest last).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    apps_dir = output_dir / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    manifest_apps: list[dict[str, object]] = []
    for app in result.applications:
        path = apps_dir / application_filename(app)
        path.write_text(canonical_newline(app.content), encoding="utf-8")
        written.append(path)
        manifest_apps.append(
            {
                "name": app.name,
                "source_file": app.source_file,
                "start_line": app.start_line,
                "end_line": app.end_line,
                "header_line": app.header_line,
                "artifact": str(path.relative_to(output_dir)).replace("\\", "/"),
            }
        )

    manifest = {
        "application_count": len(result.applications),
        "diagnostic_count": len(result.diagnostics),
        "diagnostics": [d.model_dump(mode="json") for d in result.diagnostics],
        "applications": manifest_apps,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)
    return written
