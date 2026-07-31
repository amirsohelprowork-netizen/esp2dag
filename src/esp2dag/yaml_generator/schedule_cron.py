"""Convert ESP schedule text into cron expressions when possible."""

from __future__ import annotations

import re

_TIME_RE = re.compile(r"\b(\d{1,2})[.:](\d{2})\b")


def esp_schedule_to_cron(raw: str | None) -> str | None:
    """Best-effort ESP → cron.

    Examples:
        ``11.00 DAILY ... | 19.00 DAILY ...`` → ``0 11,19 * * *``
        ``DAILY`` → ``@daily``
        ``08.03 EVERY 2 MINUTES ...`` → ``None`` (a cron cannot preserve
        the 08:03 phase, so it must be reviewed rather than approximated).
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
    if times and "DAILY" in upper:
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
        return f"{minute_part} {hour_part} * * *"

    return None
