"""Validation report builders."""

from __future__ import annotations

from collections import Counter
from typing import Any

from esp2dag.models.config import CompileResult
from esp2dag.models.diagnostics import Severity


def build_validation(result: CompileResult) -> dict[str, Any]:
    """Summarize diagnostics and failed units."""
    by_severity: Counter[str] = Counter()
    by_code: Counter[str] = Counter()
    by_stage: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    for diag in result.diagnostics:
        by_severity[diag.severity.value] += 1
        by_code[diag.code] += 1
        by_stage[diag.stage] += 1
        if len(samples) < 100:
            samples.append(
                {
                    "code": diag.code,
                    "severity": diag.severity.value,
                    "stage": diag.stage,
                    "application": diag.application,
                    "job": diag.job,
                    "message": diag.message,
                }
            )

    failures = [
        {
            "unit_id": f.unit_id,
            "stage": f.stage,
            "exception_type": f.exception_type,
            "exception_message": f.exception_message,
            "diagnostic_count": len(f.diagnostics),
        }
        for f in result.failures
    ]

    return {
        "by_severity": dict(by_severity),
        "by_code": dict(by_code.most_common()),
        "by_stage": dict(by_stage.most_common()),
        "failed_units": failures,
        "diagnostic_samples": samples,
        "has_errors": any(
            d.severity in {Severity.ERROR, Severity.FATAL} for d in result.diagnostics
        )
        or bool(result.failures),
    }


def validation_markdown(data: dict[str, Any]) -> str:
    """Render validation summary as Markdown."""
    lines = ["# Validation Report", "", "## By severity", ""]
    for sev, count in data.get("by_severity", {}).items():
        lines.append(f"- {sev}: {count}")
    lines.extend(["", "## By code", ""])
    for code, count in list(data.get("by_code", {}).items())[:30]:
        lines.append(f"- `{code}`: {count}")
    lines.extend(["", "## Failed units", ""])
    if not data.get("failed_units"):
        lines.append("- (none)")
    else:
        for unit in data["failed_units"]:
            lines.append(
                f"- `{unit['unit_id']}` @ {unit['stage']}"
                f" ({unit.get('exception_type') or 'diagnostics'})"
            )
    lines.append("")
    return "\n".join(lines)
