"""Golden tests for Phase 6 event catalog summaries."""

from __future__ import annotations

import json
from pathlib import Path

from esp2dag.event_parser import EspEventParser
from esp2dag.models.source import SourceFile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "events"
GOLDEN = Path(__file__).resolve().parent / "events"


def test_golden_clean_events_summary() -> None:
    source = SourceFile(
        path=FIXTURES / "clean_events.esp",
        content=(FIXTURES / "clean_events.esp").read_text(encoding="utf-8"),
    )
    catalog = EspEventParser().parse(source)
    actual = {
        "event_count": len(catalog.events),
        "binding_count": len(catalog.bindings),
        "events": [
            {
                "name": e.name,
                "kind": e.kind.value,
                "invoke_application": e.attributes.get("invoke_application"),
                "has_schedule": "schedule" in e.attributes,
            }
            for e in catalog.events
        ],
    }
    expected_path = GOLDEN / "clean_events.summary.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    if not expected_path.exists():
        expected_path.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected
