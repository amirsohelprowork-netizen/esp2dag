"""Convert ESP schedule text into cron expressions when possible."""

from __future__ import annotations

import re

_TIME_RE = re.compile(r"\b(\d{1,2})[.:](\d{2})\b")
_DOW = {
    "SUN": "0",
    "MON": "1",
    "TUE": "2",
    "WED": "3",
    "THU": "4",
    "FRI": "5",
    "SAT": "6",
}
_DOW_RE = re.compile(
    r"\b(SUN|MON|TUE|WED|THU|FRI|SAT|WEEKDAYS|WEEKEND)\b",
    re.I,
)


def esp_schedule_to_cron(raw: str | None) -> str | None:
    """Best-effort ESP → cron.

    Examples:
        ``11.00 DAILY ... | 19.00 DAILY ...`` → ``0 11,19 * * *``
        ``DAILY`` → ``@daily``
        ``02.15 MON ...`` → ``15 2 * * 1``
        ``08.00 WEEKDAYS`` → ``0 8 * * 1-5``
        ``08.03 EVERY 2 MINUTES ...`` → ``None`` (phase-sensitive)
    """
    if not raw:
        return None
    text = raw.strip()
    upper = text.upper()

    if upper == "DAILY":
        return "@daily"

    every_min = re.search(r"EVERY\s+(\d+)\s+MINUTES?", upper)
    if every_min:
        n = int(every_min.group(1))
        # A time-qualified ESP interval is phase-sensitive.  ``*/n`` starts
        # at the cron epoch, not at the ESP start time, so emitting it would
        # change when the job runs.
        if n <= 0 or _TIME_RE.search(text):
            return None
        if n == 1:
            return "* * * * *"
        return f"*/{n} * * * *"

    times = [(int(hour), int(minute)) for hour, minute in _TIME_RE.findall(text)]
    if not times:
        return None

    pairs = set(times)
    hours = sorted({hour for hour, _minute in pairs})
    minutes = sorted({minute for _hour, minute in pairs})
    # A single cron is exact only when the times are the complete Cartesian
    # product of the listed hours and minutes.  For example, 08:03 and
    # 09:12 cannot be represented by one cron without also scheduling
    # 08:12 and 09:03.
    if pairs != {(hour, minute) for hour in hours for minute in minutes}:
        return None

    minute_part = ",".join(str(minute) for minute in minutes)
    hour_part = ",".join(str(hour) for hour in hours)

    # ``11.00 DAILY STARTING FRI 17TH MAR 2023`` — FRI belongs to the start
    # date, not the recurrence.  Only honour DOW when DAILY is absent.
    if "DAILY" in upper:
        return f"{minute_part} {hour_part} * * *"

    dow = _day_of_week_field(upper)
    if dow is not None:
        return f"{minute_part} {hour_part} * * {dow}"
    return None


def _day_of_week_field(upper: str) -> str | None:
    """Return a cron DOW field, or None when the expression is not day-scoped."""
    if "WEEKDAYS" in upper:
        return "1-5"
    if "WEEKEND" in upper:
        return "0,6"

    found: list[str] = []
    for match in _DOW_RE.finditer(upper):
        token = match.group(1).upper()
        if token in {"WEEKDAYS", "WEEKEND"}:
            continue
        found.append(_DOW[token])
    if not found:
        return None
    # Deduplicate while preserving Sunday=0 … Saturday=6 order.
    return ",".join(sorted(set(found), key=int))
