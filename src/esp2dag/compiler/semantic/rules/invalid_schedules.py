"""Validate schedule / RUN expressions lightly."""

from __future__ import annotations

from esp2dag.compiler.ast.nodes import ApplicationNode
from esp2dag.compiler.semantic.helpers import diagnostic
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity

# Common ESP RUN calendars / keywords seen in Akron extracts.
_KNOWN_RUN_TOKENS = frozenset(
    {
        "DAILY",
        "SUN",
        "MON",
        "TUE",
        "WED",
        "THU",
        "FRI",
        "SAT",
        "WEEKDAYS",
        "WEEKENDS",
        "TODAY",
        "YESTERDAY",
        "REALNOW",
        "WORKDAYS",
        "HOLIDAY",
        "ANYDAY",
        "ONCE",
    }
)


class InvalidScheduleRule:
    """Flag empty or obviously invalid RUN expressions."""

    @property
    def name(self) -> str:
        return "invalid_schedules"

    def check(self, ast: ApplicationNode) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for job in ast.jobs:
            if job.schedule is None:
                continue
            expr = job.schedule.expression.strip()
            if not expr:
                diagnostics.append(
                    diagnostic(
                        code=DiagnosticCode.E_SEM_INVALID_SCHEDULE,
                        severity=Severity.ERROR,
                        message=f"Job '{job.name}' has an empty RUN schedule.",
                        span=job.schedule.span,
                        application=ast.name,
                        job=job.name,
                    )
                )
                continue
            # Symbolic / variable schedules (e.g. !SCHD001) are fine.
            if expr.startswith("!") or "!" in expr:
                continue
            tokens = [t for t in expr.replace(",", " ").split() if t]
            if not tokens:
                continue
            head = tokens[0].upper().strip("'\"")
            if head in _KNOWN_RUN_TOKENS or head.startswith("SCHD"):
                continue
            # Unknown calendar word — advisory only.
            diagnostics.append(
                diagnostic(
                    code=DiagnosticCode.E_SEM_INVALID_SCHEDULE,
                    severity=Severity.WARNING,
                    message=(
                        f"Job '{job.name}' RUN expression '{expr}' uses "
                        f"unrecognized schedule token '{tokens[0]}'."
                    ),
                    span=job.schedule.span,
                    application=ast.name,
                    job=job.name,
                    hint="Confirm the ESP calendar/schedule name is valid.",
                )
            )
        return diagnostics
