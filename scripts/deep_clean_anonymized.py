"""Deep-clean anonymized ESP schedule/events for public safety + scheduling focus.

Scrubs leftover business/job names, mailboxes, and paths; drops prologue/ops glue
that is not useful for schedule→DAG conversion.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANON = ROOT / "data" / "anonymized"
SCHED = ANON / "schedule.esp"
EVENTS = ANON / "events.esp"

KEEP = re.compile(
    r"^(?:"
    r"APP\d+|JOB\d+|AGENT\d+|RES\d+|QUEUE\d+|EVT\d+|USER\d+|TAG\d+|ALERT\d+|"
    r"SAP\d+|PATH\d+|DSN\d+|LIB\d+|NW_\d+|SYM\d+|SCHD\d+|MBX\d+|REDACTED\d*|"
    r"ESPAPPL|ESPEVENT|ESPJOB|BATCHUSER|CORP|SYSTEM|ESPSYS|QAFAIL\d*|"
    r"DAILY|TODAY|YESTERDAY|NOW|WAIT|REPLACE|ANYCLOSE|CREATE|NOTEXIST|"
    r"PROCESS|EXTERNAL|LINK|TASK|ADD|OK|FAIL|CONTINUE|ASAP|PRINT|YES|NO|"
    r"ALERT|MAILBOX|FAILURE|ABEND|OVERDUE|RC|REDACTED|SYNTH|SCRIPTS|"
    r"FILE|DAT|CYBROBOT|DISTRIB|CLANG|VGET|DO|ENDDO|THEN|ELSE|"
    r"JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|"
    r"MON|TUE|WED|THU|FRI|SAT|SUN|WEEKDAY|WEEKDAYS|WEEKEND|"
    r"HOURLY|WEEKLY|MONTHLY|YEARLY|ONCE|XXX|XXXXX|"
    r"NOENCORE|NODSCHECK|ESPNOMSG"
    r")$",
    re.I,
)

ESP_KEYWORDS = {
    "APPL",
    "APPLICATION",
    "ENDAPPL",
    "JOB",
    "ENDJOB",
    "NT_JOB",
    "AS400_JOB",
    "UNIX_JOB",
    "AIX_JOB",
    "LINUX_JOB",
    "SAP_JOB",
    "DATA_OBJECT",
    "AGENT_MONITOR",
    "APPLEND",
    "DSTRIG",
    "FILE_TRIGGER",
    "RUN",
    "RELEASE",
    "RESOURCE",
    "AGENT",
    "COMMAND",
    "CMDNAME",
    "SCRIPTNAME",
    "ARGS",
    "USER",
    "JOBQ",
    "NOTIFY",
    "AMNOTIFY",
    "IF",
    "THEN",
    "ELSE",
    "DO",
    "ENDDO",
    "SETVAR",
    "OPTIONS",
    "INVOKE",
    "TAG",
    "NOTWITH",
    "CCCHK",
    "DUEOUT",
    "RETRY",
    "DELAYSUB",
    "EARLYSUB",
    "SCHEDULE",
    "CALENDAR",
    "EVENT",
    "ENDDEF",
    "COM",
    "EXITCODE",
    "AFTER",
    "WAIT",
    "ADD",
    "EXTERNAL",
    "LINK",
    "PROCESS",
    "APPLID",
    "COMPLETE",
    "CHAIN",
    "ESP",
    "AJ",
    "EQ",
    "NE",
    "AND",
    "OR",
    "NORUN",
    "VARIANT",
    "ABAPNAME",
    "SAPJOBNAME",
    "SAPJOBCLASS",
    "STEPUSER",
    "STARTMODE",
    "LANGUAGE",
    "FILENAME",
    "MEMBER",
    "LIB",
    "DSNAME",
    "DATASET",
    "TRIGGER",
    "EXEC",
    "PLUS",
    "HOURS",
    "MINUTES",
    "NOCHANGE",
    "UPDATE",
    "CONTINUOUS",
    "EXIST",
}

DENY_SUBSTR = re.compile(
    r"(?i)("
    r"sales|delta|header|payment|denorm|customer|invoice|inventory|"
    r"payroll|ledger|finance|bandag|akron|aiken|bfusa|maestro|kron|"
    r"cyba_|cybb_|jda|ncd_|dts_run|boss|aiboss|aiped|aknits|"
    r"passenger|plant|bfp|zfsip|zmm|zsdb|zsd|zop_|zfi|"
    r"loadbat|extract|down_payment|to_denorm|bluemartini|"
    r"bsro|hems|reuters|tips|interfaces|/data/|/mnt/|"
    r"omniback|omniora|loyalty|posadmin|lawadm|lawbin|"
    r"brook|fujitsu|grimmett|concur|bridge|tire"
    r")"
)

IDENT = re.compile(r"\b([A-Za-z][A-Za-z0-9_#.@&!]{2,})\b")
PATHISH = re.compile(
    r"(?i)(?:[A-Za-z]:\\[^\s'\"]+|/(?:data|mnt|scripts|home|opt|var|tmp)/[^\s'\"]+)"
)


def is_keep(tok: str) -> bool:
    t = tok.strip("'\"")
    if not t:
        return True
    if t.upper() in ESP_KEYWORDS:
        return True
    if KEEP.match(t):
        return True
    if t.startswith("!"):
        return True
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return True
    if len(t) <= 2:
        return True
    return False


def looks_sensitive(tok: str) -> bool:
    if is_keep(tok):
        return False
    if "/" in tok or "\\" in tok:
        return True
    if DENY_SUBSTR.search(tok):
        return True
    if tok.count("_") >= 2 and len(tok) >= 10:
        return True
    if len(tok) >= 16 and "_" in tok:
        return True
    # Long opaque ALLCAPS names (mailboxes, team aliases)
    if len(tok) >= 8 and tok.isupper() and "_" not in tok and tok.isalpha():
        return True
    return False


def collect_sensitive(texts: list[str]) -> list[str]:
    found: set[str] = set()
    for text in texts:
        for m in PATHISH.finditer(text):
            found.add(m.group(0))
        for m in IDENT.finditer(text):
            tok = m.group(1)
            if looks_sensitive(tok):
                found.add(tok)
        for m in re.finditer(r"'([^']+)'", text):
            inner = m.group(1)
            if looks_sensitive(inner) or DENY_SUBSTR.search(inner) or "/" in inner or "\\" in inner:
                if "\n" not in inner and len(inner) < 200:
                    found.add(inner)
                for im in IDENT.finditer(inner):
                    if looks_sensitive(im.group(1)):
                        found.add(im.group(1))
    return sorted(
        (t for t in found if "\n" not in t and "\r" not in t),
        key=lambda s: (-len(s), s.upper()),
    )


def build_map(tokens: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    seen_upper: dict[str, str] = {}
    n = 0
    for tok in tokens:
        key = tok.upper()
        if key in seen_upper:
            mapping[tok] = seen_upper[key]
            continue
        n += 1
        if "/" in tok or "\\" in tok:
            synth = f"/paths/PATH{n:04d}.dat"
        else:
            synth = f"SYM{n:04d}"
        seen_upper[key] = synth
        mapping[tok] = synth
    return mapping


def apply_map(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    items = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)
    for orig, synth in items:
        text = text.replace(orig, synth)
    return text


def remap_mailboxes(text: str) -> str:
    mailboxes = sorted(set(re.findall(r"(?i)MAILBOX\(([^)]+)\)", text)), key=lambda x: -len(x))
    for i, orig in enumerate(mailboxes, 1):
        if re.fullmatch(r"MBX\d+", orig, re.I):
            continue
        text = re.sub(
            rf"(?i)MAILBOX\(\s*{re.escape(orig)}\s*\)",
            f"MAILBOX(MBX{i:04d})",
            text,
        )
    return text


def drop_prologue_and_noise(text: str) -> str:
    joined = text
    joined = re.sub(
        r"(?ims)^\s*IF\s+!USER1\s*=\s*'[^']+'\s+THEN\s*\r?\n\s*DO\s*\r?\n\s*ENDDO\s*\r?\n?",
        "",
        joined,
    )
    joined = re.sub(
        r"(?ims)^\s*IF\s+!MNFULLNAME\b.*?(?=\n\s*(?:IF\s+|JOB\s+|AS400_JOB\b|NT_JOB\b|"
        r"UNIX_JOB\b|AIX_JOB\b|LINUX_JOB\b|SAP_JOB\b|APPL\b|ENDJOB\b|DSTRIG\b|"
        r"DATA_OBJECT\b|AGENT_MONITOR\b|APPLEND\b|EXTERNAL\b|LINK\b|\Z))",
        "",
        joined,
    )
    lines = joined.splitlines()
    out: list[str] = []
    in_appl = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"(?i)^\s*APPL(?:ICATION)?\b", stripped):
            in_appl = True
        elif re.match(r"(?i)^\s*ENDAPPL\b", stripped):
            in_appl = False

        if stripped in {"/* redacted */", "COM redacted", "/*redacted*/"}:
            continue
        if re.fullmatch(r"/\*\s*redacted\s*\*/", stripped, re.I):
            continue
        if re.match(r"(?i)^\s*VGET\b", stripped):
            continue
        if re.match(r"(?i)^\s*VPUT\b", stripped):
            continue
        if re.match(r"(?i)^\s*NORUN\b", stripped):
            continue
        if re.match(r"(?i)^\s*(OPTIONS|ENCPARM)\b", stripped):
            continue
        if re.search(r"(?i)\bESP\s+AJ\b", stripped):
            continue
        if re.search(r"(?i)\bCOMPLETE\s+APPL\s*\(", stripped):
            continue
        if re.match(r"(?i)^\s*CHAIN\b", stripped):
            continue
        if not in_appl and re.match(r"(?i)^\s*RUN\s+[A-Z]{3}\s+\d{1,2}\s+\d{4}\s*$", stripped):
            continue

        line = re.sub(r"\s*/\*\s*redacted\s*\*/\s*$", "", line, flags=re.I)
        out.append(line)

    cleaned: list[str] = []
    blank = 0
    for line in out:
        if not line.strip():
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip() + "\n"


def force_scrub(text: str) -> str:
    patterns = [
        r"(?i)DS_NCD[A-Z0-9_]*",
        r"(?i)DS_JDA[A-Z0-9_]*",
        r"(?i)ZFSIP[A-Z0-9_]*",
        r"(?i)DSDNCDLC",
        r"(?i)DSDJDA\d*",
        r"(?i)AJKRON[A-Z0-9_]*",
        r"(?i)BROOKPARK[A-Z0-9_]*",
        r"(?i)FUJITSU[A-Z0-9_]*",
        r"(?i)\bBANDAG\b",
        r"(?i)\bAKRON\b",
        r"(?i)\bAIKEN\b",
        r"(?i)\bBFUSA\b",
        r"(?i)\bMAESTRO\b",
        r"(?i)CYBA_[A-Z0-9_]+",
        r"(?i)CYBB_[A-Z0-9_]+",
        r"(?i)\bbsro\b",
        r"(?i)\bhems\b",
        r"(?i)/data/[^\s'\"]+",
        r"(?i)/mnt/[^\s'\"]+",
        r"(?i)[A-Za-z]:\\[^\s'\"]+",
    ]
    for pat in patterns:
        text = re.sub(pat, "SYM_SCRUB", text)

    def scrub_ident(m: re.Match[str]) -> str:
        tok = m.group(0)
        if is_keep(tok):
            return tok
        if DENY_SUBSTR.search(tok):
            return "SYM_SCRUB"
        return tok

    return IDENT.sub(scrub_ident, text)


def verify(text: str, label: str) -> list[str]:
    hits = []
    needles = [
        "DS_NCD",
        "SALES_HDR",
        "DELTA_LOAD",
        "BANDAG",
        "AKRON",
        "AIKEN",
        "BFUSA",
        "CYBA_",
        "MAESTRO",
        "DSDNCDLC",
        "ZFSIPSALES",
        "BLUEMARTINI",
        "bsro",
        "/data/",
        "/mnt/",
        "interfaces",
        "JDAADMIN",
        "AJKRON",
        "FUJITSU",
        "BROOKPARK",
    ]
    for needle in needles:
        c = len(re.findall(re.escape(needle), text, re.I))
        if c:
            hits.append(f"{label}:{needle}x{c}")
    return hits


def main() -> None:
    schedule = SCHED.read_text(encoding="utf-8", errors="replace")
    events = EVENTS.read_text(encoding="utf-8", errors="replace")
    print("Source schedule lines", schedule.count("\n"))

    schedule = drop_prologue_and_noise(schedule)
    events = drop_prologue_and_noise(events)

    sensitive = collect_sensitive([schedule, events])
    print("Sensitive tokens", len(sensitive))
    mapping = build_map(sensitive)
    schedule = apply_map(schedule, mapping)
    events = apply_map(events, mapping)

    schedule = remap_mailboxes(schedule)
    events = remap_mailboxes(events)

    schedule = force_scrub(schedule)
    events = force_scrub(events)

    schedule = drop_prologue_and_noise(schedule)
    events = drop_prologue_and_noise(events)

    SCHED.write_text(schedule, encoding="utf-8", newline="\n")
    EVENTS.write_text(events, encoding="utf-8", newline="\n")

    leftover = verify(schedule, "schedule") + verify(events, "events")
    print("After schedule lines", schedule.count("\n"))
    print("Leftover", leftover or "NONE")


if __name__ == "__main__":
    main()
