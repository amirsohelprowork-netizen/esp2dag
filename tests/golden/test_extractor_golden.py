"""Golden tests for Phase 1 extraction manifests."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.extractor import ApplicationExtractor
from esp2dag.models.source import SourceFile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schedules"
GOLDEN = Path(__file__).resolve().parent / "extractor"


def test_golden_sample_multi_app_manifest() -> None:
    source = SourceFile(
        path=FIXTURES / "sample_multi_app.esp",
        content=(FIXTURES / "sample_multi_app.esp").read_text(encoding="utf-8"),
    )
    result = ApplicationExtractor().extract(source)
    actual = {
        "names": [a.name for a in result.applications],
        "spans": [[a.start_line, a.end_line] for a in result.applications],
        "diagnostic_codes": sorted({d.code for d in result.diagnostics}),
    }
    expected_path = GOLDEN / "sample_multi_app.manifest.json"
    if not expected_path.exists():
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected
