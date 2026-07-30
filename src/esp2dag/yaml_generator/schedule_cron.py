"""Convert ESP schedule text into cron expressions when possible."""

from __future__ import annotations

import re

_TIME_RE = re.compile(r"\b(\d{1,2})[.:](\d{2})\b")


def esp_schedule_to_cron(raw: str | None) -> str | None:
    """Best-effort ESP → cron.

    Examples:
        ``11.00 DAILY ... | 19.00 DAILY ...`` → ``0 11,19 * * *``
        ``DAILY`` → ``@daily``
        ``08.03 EVERY 2 MINUTES ...`` → ``*/2 * * * *`` (approx)
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
        if n <= 0:
            return None
        if n == 1:
            return "* * * * *"
        return f"*/{n} * * * *"

    times = _TIME_RE.findall(text)
    if times and "DAILY" in upper:
        hours = sorted({int(h) for h, _m in times})
        # If all minutes are 00, emit hour-list cron; else first minute only (simple).
        minutes = {int(m) for _h, m in times}
        if minutes == {0}:
            return f"0 {','.join(str(h) for h in hours)} * * *"
        if len(minutes) == 1:
            minute = next(iter(minutes))
            return f"{minute} {','.join(str(h) for h in hours)} * * *"
        # Mixed minutes: emit one cron per unique hour using first seen minute 0 fallback
        return f"0 {','.join(str(h) for h in hours)} * * *"

    return None
