"""Rebuild public anonymized ESP inputs from local OLD extracts.

CRITICAL: never rename ESP keywords (RELEASE, AFTER, VARIANT, STARTING, ADD, …).
That bug previously turned RELEASE→SAP973 and flattened dependency graphs.

Usage:
  python scripts/rebuild_anonymized.py

Reads:
  data/not_atonymized/schedules_OLD.esp
  data/not_atonymized/events_OLD.esp

Writes:
  data/anonymized/schedule.esp
  data/anonymized/events.esp
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OLD_SCHED = ROOT / "data" / "not_atonymized" / "schedules_OLD.esp"
OLD_EVENTS = ROOT / "data" / "not_atonymized" / "events_OLD.esp"
OUT_SCHED = ROOT / "data" / "anonymized" / "schedule.esp"
OUT_EVENTS = ROOT / "data" / "anonymized" / "events.esp"

# ---------------------------------------------------------------------------
# Keyword freeze — NEVER rename these tokens (case-insensitive whole word)
# ---------------------------------------------------------------------------
from esp2dag.compiler.lexer.token_types import JOB_TYPE_KEYWORDS, KEYWORD_MAP  # noqa: E402

_EXTRA_KEYWORDS = {
    # Job-type suffixes / kinds
    "NT_JOB",
    "AS400_JOB",
    "UNIX_JOB",
    "AIX_JOB",
    "LINUX_JOB",
    "SAP_JOB",
    "LINK_JOB",
    "TASK",
    "AGENT_MONITOR",
    "APPLEND",
    "DSTRIG",
    "FILE_TRIGGER",
    # SAP / platform fields often left as IDENTIFIER by lexer
    "VARIANT",
    "ABAPNAME",
    "SAPJOBNAME",
    "SAPJOBCLASS",
    "STEPUSER",
    "STARTMODE",
    "LANGUAGE",
    "FILENAME",
    "DSNAME",
    "DATASET",
    "MEMBER",
    "LIB",
    "AS400LIB",
    "AS400FILE",
    "ENCORE",
    "COPYJCL",
    "TEMPLIB",
    "SELFCOMPL",
    "SELFCOMPLETE",
    "WOBDATA",
    "GLOBAL",
    "LOCAL",
    "DEFINE",
    "GENTIME",
    "SUBAPPL",
    "INHERIT",
    "REL",
    "ABANDON",
    "HOLD",
    "UNHOLD",
    "BYPASS",
    "REQUEST",
    "PRIORITY",
    "MAXRUNTIME",
    "CONDCODE",
    "SEVERITY",
    "SEND",
    "EXIT",
    "EVALUATE",
    "REEXEC",
    "VS",
    "INTEGER",
    "CHARACTER",
    "ESPNOMSG",
    "TRIGGER",
    "EXEC",
    "PLUS",
    "HOURS",
    "MINUTES",
    "SECONDS",
    "NOCHANGE",
    "UPDATE",
    "CONTINUOUS",
    "EXIST",
    "CREATE",
    "ANYCLOSE",
    "NOTEXIST",
    "REPLACE",
    "COMPLETE",
    "CHAIN",
    "ESP",
    "AJ",
    "EQ",
    "NE",
    "AND",
    "OR",
    "NORUN",
    "RESTARTSTEP",
    "NORESTARTSTEP",
    "ENCPARM",
    "PREDICT",
    "DSNOTFOUND",
    "VGET",
    "VPUT",
    "CLANG",
    "COM",
    "ENDDEF",
    "ID",
    "OWNER",
    "SYSTEM",
    "SUSPEND",
    "MAILBOX",
    "ALERT",
    "FAILURE",
    "ABEND",
    "OVERDUE",
    "RC",
    "OK",
    "FAIL",
    "CONTINUE",
    "ASAP",
    "PRINT",
    "YES",
    "NO",
    "DAILY",
    "TODAY",
    "YESTERDAY",
    "NOW",
    "WAIT",
    "WEEKDAY",
    "WEEKDAYS",
    "WEEKEND",
    "HOURLY",
    "WEEKLY",
    "MONTHLY",
    "YEARLY",
    "ONCE",
    "STARTING",
    "EVERY",
    "UNTIL",
    "ON",
    "THRU",
    "THROUGH",
    "EXCEPT",
    "ONLY",
    "REALNOW",
    "DEADLINE",
    "CONDIF",
    "CONDTHEN",
    "DEPENDENCY",
    "DEP",
    # Built-in ESP vars / common leaves
    "ESPAPPL",
    "ESPEVENT",
    "ESPJOB",
    "ESPSYS",
    "BATCHUSER",
    "CORP",
    "SYSTEM",
    "SCRIPTS",
    "FILE",
    "DAT",
    "CYBROBOT",
    "DISTRIB",
    "REDACTED",
    "SYNTH",
    "PROCLIB",
    "SYS",
    "LIE",
    "LIS",
    "CDSTAT",
    "SUCCESS",
    "WARNING",
    "INFO",
    "CRITICAL",
    "NORMAL",
    "ANY",
    "ALL",
    "NONE",
    "JOBNAME",
    "APPLNAME",
    "FULLNAME",
    "MNFULLNAME",
    "USER1",
    "SCHD",
    # Calendar fragments
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
    "MON",
    "TUE",
    "WED",
    "THU",
    "FRI",
    "SAT",
    "SUN",
    "ST",
    "ND",
    "RD",
    "TH",
    "1ST",
    "2ND",
    "3RD",
    "4TH",
    "5TH",
    "6TH",
    "7TH",
    "8TH",
    "9TH",
    "10TH",
    "11TH",
    "12TH",
    "13TH",
    "14TH",
    "15TH",
    "16TH",
    "17TH",
    "18TH",
    "19TH",
    "20TH",
    "21ST",
    "22ND",
    "23RD",
    "24TH",
    "25TH",
    "26TH",
    "27TH",
    "28TH",
    "29TH",
    "30TH",
    "31ST",
}

ESP_KEYWORDS: frozenset[str] = frozenset(
    {k.upper() for k in KEYWORD_MAP}
    | {k.upper() for k in JOB_TYPE_KEYWORDS}
    | {k.upper() for k in _EXTRA_KEYWORDS}
)

# Org / product denylist — force scrub if still present after mapping
DENY_SUBSTR = re.compile(
    r"(?i)("
    r"bandag|akron|aiken|bfusa|maestro|bridgestone|goodyear|"
    r"cyba_|cybb_|ds_ncd|ds_jda|zfsipsales|dsdncdlc|dsdjda|"
    r"bluemartini|bsro\b|hems\b"
    r")"
)

# Identifiers that can reveal an estate even after business names and job ids
# have been tokenized.  These are replaced after normal token substitution so
# paths, notification bodies, and event payloads are also covered.
_EMAIL_RE = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
_PRIVATE_IPV4_RE = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
_UNC_HOST_RE = re.compile(r"(?i)\\\\(?!AGENT\d+\b|SYM\d+\b)[^\\\s'\"+]+")
_QUOTED_DSTRIG_RE = re.compile(r"(?i)(\bDSTRIG\s+)'[^']+'")
_RESIDUAL_TERMS_RE = re.compile(
    r"(?i)\b(?:polkdatauploadssis|adw|cti-rms|bacs|wty|equitble|unmeth|"
    r"dcexpt|dcftsc|dcnatl|dcrent|dcretl|dcwwork)\b"
)

IDENT = re.compile(r"\b([A-Za-z][!A-Za-z0-9_#.@*]{0,80})\b")
PUBLIC_TOKEN = re.compile(r"\b([A-Za-z][!A-Za-z0-9_#.@*-]{2,80})\b")
PATHISH = re.compile(
    r"(?i)(?:[A-Za-z]:\\[^\s'\"]+|/(?:data|mnt|home|opt|var|tmp|scripts)/[^\s'\"]+)"
)
QUOTED = re.compile(r"'([^']*)'")

APPL_HDR = re.compile(
    r"(?im)^\s*(?:APPL(?:ICATION)?)\s+([A-Za-z0-9_#.@!+-]+)"
)
JOB_HDR = re.compile(
    r"(?im)^\s*(?:NT_JOB|AS400_JOB|UNIX_JOB|AIX_JOB|LINUX_JOB|SAP_JOB|"
    r"DATA_OBJECT|AGENT_MONITOR|APPLEND|DSTRIG|FILE_TRIGGER|JOB)\s+"
    r"([A-Za-z0-9_#.@!+-]+)"
)
AGENT_REF = re.compile(r"(?im)^\s*AGENT\s+([A-Za-z0-9_#.@!+-]+)")
MAILBOX_REF = re.compile(r"(?i)MAILBOX\(([^)]+)\)")
ALERT_REF = re.compile(r"(?i)ALERT\(([^)]+)\)")
EVENT_ID = re.compile(r"(?i)\bEVENT\s+ID\s*\(\s*([A-Za-z0-9_#.@!+-]+)\s*\)")
RESOURCE_NAME = re.compile(
    r"(?i)\bRESOURCE\s+ADD\s*\(\s*[^,)]+\s*,\s*([A-Za-z0-9_#.@!+-]+)\s*\)"
)
# Job names referenced by dependency / release statements (may not have a header nearby)
DEP_TARGET = re.compile(
    r"(?i)\b(?:RELEASE|AFTER)\s+(?:ADD\s*)?\(\s*([A-Za-z0-9_#.@!+-]+)"
)


class NameAllocator:
    def __init__(self) -> None:
        self._maps: dict[str, dict[str, str]] = {
            "APP": {},
            "JOB": {},
            "AGENT": {},
            "MBX": {},
            "ALERT": {},
            "EVT": {},
            "RES": {},
            "PATH": {},
            "SYM": {},
            "USER": {},
        }
        self._counts: dict[str, int] = {k: 0 for k in self._maps}

    def get(self, kind: str, original: str) -> str:
        key = original.upper()
        bucket = self._maps[kind]
        if key in bucket:
            return bucket[key]
        self._counts[kind] += 1
        width = 4 if self._counts[kind] < 10000 else 5
        synth = f"{kind}{self._counts[kind]:0{width}d}"
        bucket[key] = synth
        return synth


def is_frozen(tok: str) -> bool:
    t = tok.strip("'\"")
    if not t:
        return True
    if t.upper() == "SYS.ESP.PROCLIB":
        return True
    if "." in t or "-" in t:
        parts = [part for part in re.split(r"[.-]", t) if part]
        if parts and all(is_frozen(part) for part in parts):
            return True
    if t.startswith("!"):
        # !ESPAPPL etc. — freeze the leaf after !
        leaf = t[1:].split(".", 1)[-1]
        if leaf.upper() in ESP_KEYWORDS:
            return True
        # still allow renaming of !BUSINESS_NAME
        if leaf.upper() in ESP_KEYWORDS or t[1:].upper() in ESP_KEYWORDS:
            return True
    if t.upper() in ESP_KEYWORDS:
        return True
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return True
    if len(t) <= 1:
        return True
    # already synthetic
    if re.fullmatch(
        r"(?:APP|JOB|AGENT|MBX|ALERT|EVT|RES|PATH|SYM|USER|SAP|DSN|LIB|NW_|ANON)\d+",
        t,
        re.I,
    ):
        return True
    return False


def looks_business(tok: str) -> bool:
    if is_frozen(tok):
        return False
    if "/" in tok or "\\" in tok:
        return True
    if DENY_SUBSTR.search(tok):
        return True
    if tok.count("_") >= 1 and len(tok) >= 6:
        return True
    if tok.count("_") >= 2 and len(tok) >= 8:
        return True
    if len(tok) >= 12 and "_" in tok:
        return True
    # Opaque all-caps / alphanumeric job-like tokens (RTTAPCCS, USUCCVMS, …)
    if len(tok) >= 6 and re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", tok):
        return True
    return False


def strip_noise(text: str) -> str:
    """Light cleanup: comments, VGET prologue — keep all ESP keywords intact."""
    # Block / line comments → short placeholder
    text = re.sub(r"/\*.*?\*/", "/* redacted */", text, flags=re.S)
    text = re.sub(r"(?im)^\s*COM\b.*$", "COM redacted", text)

    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"(?i)^\s*VGET\b", stripped):
            continue
        if re.match(r"(?i)^\s*VPUT\b", stripped):
            continue
        out.append(line.rstrip())

    cleaned: list[str] = []
    blank = 0
    for line in out:
        if not line.strip():
            blank += 1
            if blank <= 2:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def catalog(text: str, alloc: NameAllocator) -> None:
    for m in APPL_HDR.finditer(text):
        name = m.group(1)
        if not is_frozen(name):
            alloc.get("APP", name)

    for m in JOB_HDR.finditer(text):
        name = m.group(1)
        # Skip qualifiers like LIE.!ESPAPPL — rename LIE part separately via SYM if needed
        if not is_frozen(name):
            # EXTERNAL/LINK names still get JOB ids when they are job headers
            alloc.get("JOB", name.split("(", 1)[0])

    for m in AGENT_REF.finditer(text):
        name = m.group(1)
        if not is_frozen(name):
            alloc.get("AGENT", name)

    for m in MAILBOX_REF.finditer(text):
        name = m.group(1).strip()
        if not is_frozen(name):
            alloc.get("MBX", name)

    for m in ALERT_REF.finditer(text):
        name = m.group(1).strip()
        if not is_frozen(name):
            alloc.get("ALERT", name)

    for m in EVENT_ID.finditer(text):
        name = m.group(1).strip()
        if not is_frozen(name):
            alloc.get("EVT", name)

    for m in RESOURCE_NAME.finditer(text):
        name = m.group(1).strip()
        if not is_frozen(name):
            alloc.get("RES", name)

    for m in DEP_TARGET.finditer(text):
        name = m.group(1).strip()
        if name and not is_frozen(name):
            # Prefer JOB id so RELEASE ADD(peer) stays consistent with headers
            leaf = name.split(".", 1)[0]
            if leaf.upper() not in {"LIE", "LIS", "CDSTAT"} and not is_frozen(leaf):
                alloc.get("JOB", name.split("(", 1)[0])

    for m in PATHISH.finditer(text):
        alloc.get("PATH", m.group(0))

    # USER CORP\foo or USER domain\user
    for m in re.finditer(r"(?im)^\s*USER\s+(\S+)", text):
        name = m.group(1)
        if not is_frozen(name) and ("\\" in name or looks_business(name)):
            alloc.get("USER", name)


def build_replacement_table(alloc: NameAllocator, texts: list[str]) -> list[tuple[str, str]]:
    """Longest-first (original, synth) pairs from catalogs + free-text business tokens.

    Priority when the same original appears in multiple catalogs:
    APP > JOB > AGENT > EVT > RES > USER > MBX > ALERT > PATH > SYM
    so application/job ids are not overwritten by mailbox/alert aliases.
    """
    pairs: dict[str, str] = {}
    priority = ["APP", "JOB", "AGENT", "EVT", "RES", "USER", "MBX", "ALERT", "PATH", "SYM"]

    for kind in priority:
        bucket = alloc._maps[kind]
        for orig_u, synth in bucket.items():
            if orig_u not in pairs:
                pairs[orig_u] = synth

    # Harvest additional business identifiers (not frozen)
    for text in texts:
        for m in IDENT.finditer(text):
            tok = m.group(1)
            if is_frozen(tok):
                continue
            if looks_business(tok):
                key = tok.upper()
                if key not in pairs:
                    pairs[key] = alloc.get("SYM", tok)

        for m in QUOTED.finditer(text):
            inner = m.group(1)
            if not inner or "\n" in inner:
                continue
            # Full quoted path / business filename
            if looks_business(inner) or DENY_SUBSTR.search(inner) or "/" in inner or "\\" in inner:
                key = inner.upper()
                if key not in pairs and len(inner) < 240:
                    if "/" in inner or "\\" in inner:
                        pairs[key] = alloc.get("PATH", inner)
                    else:
                        pairs[key] = alloc.get("SYM", inner)

    items = sorted(pairs.items(), key=lambda kv: len(kv[0]), reverse=True)
    return items


def apply_replacements(text: str, items: list[tuple[str, str]]) -> str:
    """Replace using case-insensitive whole-token / path matching. Never touch frozen keywords."""

    # Paths first (exact, case-insensitive)
    path_items = [(o, s) for o, s in items if "/" in o or "\\" in o]
    other_items = [(o, s) for o, s in items if "/" not in o and "\\" not in o]

    for orig_u, synth in path_items:
        # synth for PATH kind is PATH#### — wrap as synthetic path
        if re.fullmatch(r"PATH\d+", synth, re.I):
            repl = f"/paths/{synth}.dat"
        else:
            repl = synth
        text = re.sub(re.escape(orig_u), repl, text, flags=re.I)

    # Build regex for identifiers: longest first alternation is huge; apply per-token
    # Use a function on IDENT matches for safety with freeze list.
    lookup = {o.upper(): s for o, s in other_items}

    def repl_ident(m: re.Match[str]) -> str:
        tok = m.group(1)
        if is_frozen(tok):
            return tok
        # Handle dotted names: FOO.BAR → map each segment if present
        if "." in tok and not tok.startswith("!"):
            parts = tok.split(".")
            out_parts = []
            for p in parts:
                if is_frozen(p):
                    out_parts.append(p)
                else:
                    out_parts.append(lookup.get(p.upper(), p))
            # If whole token mapped, prefer that
            whole = lookup.get(tok.upper())
            return whole if whole else ".".join(out_parts)
        if tok.startswith("!"):
            leaf = tok[1:]
            if is_frozen(tok) or is_frozen(leaf):
                return tok
            mapped = lookup.get(leaf.upper())
            return f"!{mapped}" if mapped else tok
        return lookup.get(tok.upper(), tok)

    text = IDENT.sub(repl_ident, text)

    # MAILBOX / ALERT already covered if names are in lookup; ensure paren forms
    def repl_mailbox(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        if is_frozen(inner):
            return m.group(0)
        synth = lookup.get(inner.upper())
        return f"MAILBOX({synth})" if synth else m.group(0)

    def repl_alert(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        if is_frozen(inner):
            return m.group(0)
        synth = lookup.get(inner.upper())
        return f"ALERT({synth})" if synth else m.group(0)

    text = MAILBOX_REF.sub(repl_mailbox, text)
    text = ALERT_REF.sub(repl_alert, text)

    # Quoted strings: replace known inners
    def repl_quoted(m: re.Match[str]) -> str:
        inner = m.group(1)
        key = inner.upper()
        if key in lookup:
            synth = lookup[key]
            if re.fullmatch(r"PATH\d+", synth, re.I):
                synth = f"/paths/{synth}.dat"
            return f"'{synth}'"
        # remap idents inside quote without destroying structure keywords
        def qi(mm: re.Match[str]) -> str:
            t = mm.group(1)
            if is_frozen(t):
                return t
            return lookup.get(t.upper(), t)

        return "'" + IDENT.sub(qi, inner) + "'"

    text = QUOTED.sub(repl_quoted, text)
    return text


def force_deny_scrub(text: str) -> str:
    """Last-pass scrub of denylist fragments without touching frozen keywords."""

    def scrub_ident(m: re.Match[str]) -> str:
        tok = m.group(0)
        if is_frozen(tok):
            return tok
        if DENY_SUBSTR.search(tok):
            return "SYM_SCRUB"
        return tok

    text = IDENT.sub(scrub_ident, text)
    # Hard patterns
    for pat in [
        r"(?i)DS_NCD[A-Z0-9_]*",
        r"(?i)DS_JDA[A-Z0-9_]*",
        r"(?i)ZFSIPSALES[A-Z0-9_]*",
        r"(?i)DSDNCDLC",
        r"(?i)DSDJDA\d*",
        r"(?i)\bBANDAG\b",
        r"(?i)\bAKRON\b",
        r"(?i)\bAIKEN\b",
        r"(?i)\bBFUSA\b",
        r"(?i)\bMAESTRO\b",
        r"(?i)CYBA_[A-Z0-9_]+",
        r"(?i)CYBB_[A-Z0-9_]+",
        r"(?i)\bbsro\b",
    ]:
        text = re.sub(pat, "SYM_SCRUB", text)
    # Remove infrastructure/network details and free-text notification
    # recipients.  RFC 2606's example.invalid is intentionally non-routable.
    text = _EMAIL_RE.sub("EMAIL_REDACTED@example.invalid", text)
    text = _PRIVATE_IPV4_RE.sub("192.0.2.10", text)
    text = _UNC_HOST_RE.sub(r"\\\\HOST_REDACTED", text)
    # Dataset names commonly encode business systems and feeds.  Retain the
    # DSTRIG shape, not the original identifier.
    text = _QUOTED_DSTRIG_RE.sub(r"\1'SYNTH.DATASET.REDACTED.G-'", text)
    text = _RESIDUAL_TERMS_RE.sub("SYM_SCRUB", text)
    return text


def strict_public_scrub(texts: list[str]) -> list[str]:
    """Replace residual human/business tokens in an already-redacted export.

    This is intentionally stricter than the source-to-source mapper.  It is
    for public demo data: a token that is not an ESP keyword or synthetic id
    is treated as identifying and is replaced consistently across both files.
    """
    mapping: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        if is_frozen(token):
            return token
        key = token.upper()
        if key not in mapping:
            mapping[key] = f"ANON{len(mapping) + 1:05d}"
        return mapping[key]

    return [PUBLIC_TOKEN.sub(repl, text) for text in texts]


def assert_healthy(schedule: str, events: str) -> None:
    release = len(re.findall(r"(?i)\bRELEASE\b", schedule))
    release_add = len(re.findall(r"(?i)\bRELEASE\s+ADD\b", schedule))
    after = len(re.findall(r"(?i)\bAFTER\b", schedule))
    after_add = len(re.findall(r"(?i)\bAFTER\s+ADD\b", schedule))
    variant = len(re.findall(r"(?i)\bVARIANT\b", schedule))
    starting = len(re.findall(r"(?i)\bSTARTING\b", events))
    sap973_add = len(re.findall(r"(?i)\bSAP973\s+ADD\b", schedule))
    bad_release = len(re.findall(r"(?i)\bSAP\d+\s+ADD\b", schedule))

    print(
        f"ASSERT RELEASE={release} RELEASE_ADD={release_add} "
        f"AFTER={after} AFTER_ADD={after_add} VARIANT={variant} STARTING={starting}"
    )
    print(f"ASSERT SAP973_ADD={sap973_add} SAP##_ADD={bad_release}")

    errors: list[str] = []
    if release < 1000:
        errors.append(f"RELEASE too low ({release})")
    if release_add < 1000:
        errors.append(f"RELEASE ADD too low ({release_add})")
    if after_add < 10:
        errors.append(f"AFTER ADD too low ({after_add})")
    if variant < 500:
        errors.append(f"VARIANT too low ({variant})")
    if starting < 1:
        errors.append("STARTING missing from events")
    if sap973_add:
        errors.append(f"SAP973 ADD still present ({sap973_add})")
    # SAP#### ADD should only happen if someone named a job SAP973 — flag high counts
    if bad_release > 10:
        errors.append(f"Suspicious SAP#### ADD count ({bad_release})")

    for label, text in ("schedule", schedule), ("events", events):
        for needle in [
            "DS_NCD_SALES",
            "BANDAG",
            "AKRON",
            "AIKEN",
            "BFUSA",
            "MAESTRO",
            "BLUEMARTINI",
            "DSDNCDLC",
            "ZFSIPSALES",
            "ONMICROSOFT.COM",
            "ROC-GROUP.COM",
            "CDC1-AK-FIS",
            "BHPFTP",
            "POLKDATAUPLOADSSIS",
        ]:
            if re.search(re.escape(needle), text, re.I):
                errors.append(f"{label} still contains {needle}")
        if any(
            not email.lower().endswith("@example.invalid")
            for email in _EMAIL_RE.findall(text)
        ):
            errors.append(f"{label} still contains an email address")
        if _PRIVATE_IPV4_RE.search(text):
            errors.append(f"{label} still contains a private IPv4 address")

    # Keywords must not have been turned into SAP#### as a statement verb
    for kw in ("RELEASE", "VARIANT", "STARTING", "ADD", "RESOURCE", "AFTER"):
        if kw.upper() not in ESP_KEYWORDS:
            errors.append(f"freeze list missing {kw}")

    if errors:
        raise SystemExit("Anonymization health check FAILED:\n  - " + "\n  - ".join(errors))
    print("Health check OK")


def rescrub_public_inputs() -> None:
    """Apply the strict public-data scrub without requiring private inputs."""
    schedule = OUT_SCHED.read_text(encoding="utf-8", errors="replace")
    events = OUT_EVENTS.read_text(encoding="utf-8", errors="replace")
    schedule = force_deny_scrub(schedule)
    events = force_deny_scrub(events)
    schedule, events = strict_public_scrub([schedule, events])
    # The strict pass can expose address-like fragments; make a final direct
    # scrub so no routable recipient or private address remains.
    schedule = force_deny_scrub(schedule)
    events = force_deny_scrub(events)
    OUT_SCHED.write_text(schedule, encoding="utf-8", newline="\n")
    OUT_EVENTS.write_text(events, encoding="utf-8", newline="\n")
    assert_healthy(schedule, events)


def main() -> None:
    if "--rescrub-public" in sys.argv:
        rescrub_public_inputs()
        return
    if not OLD_SCHED.exists() or not OLD_EVENTS.exists():
        raise SystemExit(
            f"Missing OLD inputs.\n  {OLD_SCHED}\n  {OLD_EVENTS}\n"
            "Place private extracts under data/not_atonymized/ (gitignored)."
        )

    schedule = OLD_SCHED.read_text(encoding="utf-8", errors="replace")
    events = OLD_EVENTS.read_text(encoding="utf-8", errors="replace")
    # Drop CSV-ish header if present
    if events.lstrip().startswith("Column1"):
        events = events.split("\n", 1)[-1]

    print(f"OLD schedule lines={schedule.count(chr(10))} events={events.count(chr(10))}")
    print(f"Freeze list size={len(ESP_KEYWORDS)} (RELEASE frozen={('RELEASE' in ESP_KEYWORDS)})")

    schedule = strip_noise(schedule)
    events = strip_noise(events)

    alloc = NameAllocator()
    catalog(schedule, alloc)
    catalog(events, alloc)
    print(
        "Catalog:",
        {k: len(v) for k, v in alloc._maps.items() if v},
    )

    items = build_replacement_table(alloc, [schedule, events])
    print(f"Replacement pairs: {len(items)}")

    schedule = apply_replacements(schedule, items)
    events = apply_replacements(events, items)

    schedule = force_deny_scrub(schedule)
    events = force_deny_scrub(events)
    schedule, events = strict_public_scrub([schedule, events])
    schedule = force_deny_scrub(schedule)
    events = force_deny_scrub(events)

    # Keep SYS.ESP.PROCLIB structural if somehow remapped — restore common form
    schedule = re.sub(
        r"(?i)INVOKE\s+'[^']*PROCLIB\(",
        "INVOKE 'SYS.ESP.PROCLIB(",
        schedule,
    )
    events = re.sub(
        r"(?i)INVOKE\s+'[^']*PROCLIB\(",
        "INVOKE 'SYS.ESP.PROCLIB(",
        events,
    )

    OUT_SCHED.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCHED.write_text(schedule, encoding="utf-8", newline="\n")
    OUT_EVENTS.write_text(events, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_SCHED} ({schedule.count(chr(10))} lines)")
    print(f"Wrote {OUT_EVENTS} ({events.count(chr(10))} lines)")

    assert_healthy(schedule, events)


if __name__ == "__main__":
    main()
