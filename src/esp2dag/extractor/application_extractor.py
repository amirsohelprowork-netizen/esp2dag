"""Phase 1: Application Extractor.

Splits a large ESP schedule file into in-memory ``SourceApplication`` units.

Real ESP schedules (e.g. Akron/Bandag extracts) use::

    APPL APPNAME [options...]
    ...
    APPL NEXTAPP ...

There is typically **no** ``ENDAPPL``. Application boundaries are:

1. Start: a statement whose first keyword is ``APPL`` or ``APPLICATION``
2. End: the line before the next application start, an ``ENDAPPL`` if present,
   or EOF

This stage does **not** parse jobs. It only separates applications while
preserving source line numbers and file references.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from esp2dag.compiler.context import ExtractResult
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity
from esp2dag.models.source import SourceApplication, SourceFile, SourceSpan

logger = logging.getLogger(__name__)

STAGE = "extractor"

# First keyword on a statement line (comments stripped).
_APPL_START_RE = re.compile(
    r"^(?P<kw>APPLICATION|APPL)\s+(?P<name>\S+)",
    re.IGNORECASE,
)
_APPL_END_RE = re.compile(r"^ENDAPPL\b", re.IGNORECASE)
_NON_WHITESPACE_RE = re.compile(r"\S")


@dataclass(frozen=True, slots=True)
class _ApplStart:
    """Internal marker for an application start line."""

    line_number: int  # 1-based
    name: str
    header_line: str
    column: int


class ApplicationExtractor:
    """Split a schedule file into ``SourceApplication`` units.

    Fault isolation: malformed constructs produce diagnostics; extraction
    continues for remaining applications.
    """

    def extract(self, source: SourceFile) -> ExtractResult:
        """Extract application units from a schedule source file.

        Args:
            source: Loaded schedule file.

        Returns:
            Applications in source order plus structured diagnostics.
        """
        logger.info("Extracting applications from %s", source.path_str)
        content = source.content.lstrip("\ufeff")
        lines = content.splitlines(keepends=True)
        if not content:
            return ExtractResult(
                applications=[],
                diagnostics=[
                    Diagnostic(
                        code=DiagnosticCode.E_EXTRACT_NO_APPS,
                        severity=Severity.ERROR,
                        message="Schedule file is empty; no applications found.",
                        stage=STAGE,
                        span=SourceSpan(
                            file=source.path_str,
                            start_line=1,
                            end_line=1,
                        ),
                    )
                ],
            )

        starts, scan_diagnostics = self._scan_boundaries(lines, source.path_str)
        diagnostics: list[Diagnostic] = list(scan_diagnostics)

        if not starts:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.E_EXTRACT_NO_APPS,
                    severity=Severity.ERROR,
                    message="No APPL/APPLICATION statements found in schedule file.",
                    stage=STAGE,
                    span=SourceSpan(
                        file=source.path_str,
                        start_line=1,
                        end_line=max(1, len(lines)),
                    ),
                    hint="Expected lines starting with APPL <name> or APPLICATION <name>.",
                )
            )
            return ExtractResult(applications=[], diagnostics=diagnostics)

        diagnostics.extend(self._prologue_diagnostics(lines, starts[0], source.path_str))
        diagnostics.extend(self._duplicate_name_diagnostics(starts, source.path_str))

        applications: list[SourceApplication] = []
        total_lines = len(lines)

        for index, start in enumerate(starts):
            next_start_line = (
                starts[index + 1].line_number if index + 1 < len(starts) else None
            )
            try:
                app, app_diags = self._build_application(
                    lines=lines,
                    start=start,
                    next_start_line=next_start_line,
                    total_lines=total_lines,
                    source_file=source.path_str,
                )
                applications.append(app)
                diagnostics.extend(app_diags)
            except Exception as exc:  # noqa: BLE001 - isolate per application
                logger.exception(
                    "Failed to extract application %s at line %s",
                    start.name,
                    start.line_number,
                )
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCode.E_EXTRACT_UNCLOSED_APP,
                        severity=Severity.ERROR,
                        message=(
                            f"Failed to extract application '{start.name}': "
                            f"{type(exc).__name__}: {exc}"
                        ),
                        stage=STAGE,
                        application=start.name,
                        span=SourceSpan(
                            file=source.path_str,
                            start_line=start.line_number,
                            start_column=start.column,
                            end_line=start.line_number,
                            end_column=start.column,
                            text=start.header_line.strip("\n"),
                        ),
                    )
                )

        logger.info(
            "Extracted %d application(s) from %s (%d diagnostic(s))",
            len(applications),
            source.path_str,
            len(diagnostics),
        )
        return ExtractResult(applications=applications, diagnostics=diagnostics)

    def _scan_boundaries(
        self,
        lines: list[str],
        source_file: str,
    ) -> tuple[list[_ApplStart], list[Diagnostic]]:
        """Find APPL starts and orphan ENDAPPL markers."""
        starts: list[_ApplStart] = []
        diagnostics: list[Diagnostic] = []
        in_block_comment = False
        open_app: _ApplStart | None = None

        for line_number, raw in enumerate(lines, start=1):
            code, in_block_comment = strip_esp_comments(raw, in_block_comment)
            stripped = code.strip()
            if not stripped:
                continue

            start_match = _APPL_START_RE.match(stripped)
            if start_match:
                column = _leading_indent_width(raw) + 1
                start = _ApplStart(
                    line_number=line_number,
                    name=start_match.group("name"),
                    header_line=raw.rstrip("\r\n"),
                    column=column,
                )
                starts.append(start)
                open_app = start
                continue

            if _APPL_END_RE.match(stripped):
                if open_app is None:
                    diagnostics.append(
                        Diagnostic(
                            code=DiagnosticCode.E_EXTRACT_ORPHAN_ENDAPPL,
                            severity=Severity.ERROR,
                            message="Found ENDAPPL without a matching APPL/APPLICATION.",
                            stage=STAGE,
                            span=SourceSpan(
                                file=source_file,
                                start_line=line_number,
                                end_line=line_number,
                                text=raw.rstrip("\r\n"),
                            ),
                        )
                    )
                else:
                    open_app = None

        return starts, diagnostics

    def _build_application(
        self,
        *,
        lines: list[str],
        start: _ApplStart,
        next_start_line: int | None,
        total_lines: int,
        source_file: str,
    ) -> tuple[SourceApplication, list[Diagnostic]]:
        """Build one ``SourceApplication`` from line range."""
        diagnostics: list[Diagnostic] = []
        natural_end = (next_start_line - 1) if next_start_line is not None else total_lines
        end_line = natural_end
        endappl_line = self._find_endappl(lines, start.line_number, natural_end)

        if endappl_line is not None:
            end_line = endappl_line
            if endappl_line < natural_end and self._has_code_between(
                lines, endappl_line + 1, natural_end
            ):
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCode.W_EXTRACT_INTERSTITIAL,
                        severity=Severity.WARNING,
                        message=(
                            f"Content after ENDAPPL for '{start.name}' "
                            f"(lines {endappl_line + 1}-{natural_end}) "
                            "is outside any application."
                        ),
                        stage=STAGE,
                        application=start.name,
                        span=SourceSpan(
                            file=source_file,
                            start_line=endappl_line + 1,
                            end_line=natural_end,
                        ),
                        hint="Move orphaned statements into an APPL block.",
                    )
                )

        slice_lines = lines[start.line_number - 1 : end_line]
        content = "".join(slice_lines)
        # Normalize to \n for deterministic in-memory content while preserving text.
        if content.endswith("\r\n") or "\r\n" in content:
            # Keep original newlines from source slice as-is for fidelity.
            pass

        app = SourceApplication(
            name=start.name,
            source_file=source_file,
            start_line=start.line_number,
            end_line=end_line,
            content=content,
            header_line=start.header_line,
        )

        if self._is_effectively_empty(slice_lines):
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.W_EXTRACT_EMPTY_APP,
                    severity=Severity.WARNING,
                    message=f"Application '{start.name}' has no body statements.",
                    stage=STAGE,
                    application=start.name,
                    span=app.span,
                )
            )

        return app, diagnostics

    def _find_endappl(self, lines: list[str], start_line: int, end_line: int) -> int | None:
        """Return 1-based line of ENDAPPL within [start_line, end_line], if any."""
        in_block_comment = False
        # Comment state from file start would be more accurate; re-scan from start_line
        # is insufficient if a block comment opened earlier. Re-scan from line 1 to
        # start_line-1 for comment state only when needed — see _comment_state_at.
        in_block_comment = self._comment_state_at(lines, start_line)
        for line_number in range(start_line, end_line + 1):
            raw = lines[line_number - 1]
            code, in_block_comment = strip_esp_comments(raw, in_block_comment)
            if _APPL_END_RE.match(code.strip()):
                return line_number
        return None

    def _comment_state_at(self, lines: list[str], line_number: int) -> bool:
        """Return whether a block comment is open at the start of ``line_number``."""
        in_block_comment = False
        for raw in lines[: line_number - 1]:
            _, in_block_comment = strip_esp_comments(raw, in_block_comment)
        return in_block_comment

    def _has_code_between(self, lines: list[str], start_line: int, end_line: int) -> bool:
        """True if any non-comment code exists in the inclusive line range."""
        in_block_comment = self._comment_state_at(lines, start_line)
        for line_number in range(start_line, end_line + 1):
            code, in_block_comment = strip_esp_comments(
                lines[line_number - 1], in_block_comment
            )
            if _NON_WHITESPACE_RE.search(code):
                return True
        return False

    def _is_effectively_empty(self, slice_lines: list[str]) -> bool:
        """True when only the APPL header (and comments/blank lines) are present."""
        if not slice_lines:
            return True
        in_block_comment = False
        saw_header = False
        for raw in slice_lines:
            code, in_block_comment = strip_esp_comments(raw, in_block_comment)
            stripped = code.strip()
            if not stripped:
                continue
            if not saw_header and _APPL_START_RE.match(stripped):
                saw_header = True
                continue
            return False
        return True

    def _prologue_diagnostics(
        self,
        lines: list[str],
        first: _ApplStart,
        source_file: str,
    ) -> list[Diagnostic]:
        """Warn about non-comment content before the first APPL."""
        if first.line_number <= 1:
            return []
        if not self._has_code_between(lines, 1, first.line_number - 1):
            return []
        return [
            Diagnostic(
                code=DiagnosticCode.W_EXTRACT_PROLOGUE,
                severity=Severity.WARNING,
                message=(
                    f"Schedule contains {first.line_number - 1} line(s) before the "
                    f"first APPL ('{first.name}' at line {first.line_number})."
                ),
                stage=STAGE,
                span=SourceSpan(
                    file=source_file,
                    start_line=1,
                    end_line=first.line_number - 1,
                ),
                hint=(
                    "Prologue statements are not attached to an application; "
                    "review manually if they contain jobs or controls."
                ),
            )
        ]

    def _duplicate_name_diagnostics(
        self,
        starts: list[_ApplStart],
        source_file: str,
    ) -> list[Diagnostic]:
        """Emit warnings for repeated application names (still extracted separately)."""
        seen: dict[str, int] = {}
        diagnostics: list[Diagnostic] = []
        for start in starts:
            key = start.name.upper()
            if key in seen:
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCode.W_EXTRACT_DUPLICATE_NAME,
                        severity=Severity.WARNING,
                        message=(
                            f"Duplicate application name '{start.name}' at line "
                            f"{start.line_number} (first seen at line {seen[key]})."
                        ),
                        stage=STAGE,
                        application=start.name,
                        span=SourceSpan(
                            file=source_file,
                            start_line=start.line_number,
                            start_column=start.column,
                            end_line=start.line_number,
                            text=start.header_line,
                        ),
                        hint="Both units are extracted; semantic analysis will also flag this.",
                    )
                )
            else:
                seen[key] = start.line_number
        return diagnostics


def strip_esp_comments(line: str, in_block_comment: bool = False) -> tuple[str, bool]:
    """Remove ESP comment regions from a line.

    ESP schedule extracts commonly use:

    - ``/* comment */`` on one line
    - ``/* comment`` with **no** closing ``*/`` meaning *rest of line* is comment

    Multi-line block comments that omit ``*/`` are therefore treated as
    end-of-line comments so subsequent ``APPL`` boundaries are not swallowed.

    Args:
        line: Raw source line (newline optional).
        in_block_comment: Unused; retained for API compatibility with callers.

    Returns:
        Tuple of (code_without_comments, False).
    """
    _ = in_block_comment
    result: list[str] = []
    i = 0
    length = len(line)
    while i < length:
        # Preserve newlines outside comment stripping.
        if line[i] == "\n":
            result.append("\n")
            i += 1
            continue
        if line[i] == "\r":
            result.append("\r")
            i += 1
            continue

        open_idx = line.find("/*", i)
        if open_idx == -1:
            result.append(line[i:])
            break

        result.append(line[i:open_idx])
        close_idx = line.find("*/", open_idx + 2)
        newline_idx = _find_newline(line, open_idx + 2)

        if close_idx != -1 and (newline_idx == -1 or close_idx < newline_idx):
            # Closed block comment on this line — skip the comment span.
            i = close_idx + 2
            continue

        # Unclosed /* → comment through end of line (keep newline if present).
        if newline_idx == -1:
            break
        result.append(line[newline_idx])
        i = newline_idx + 1

    return "".join(result), False


def _find_newline(text: str, start: int) -> int:
    """Return index of the next ``\\n``, or -1."""
    return text.find("\n", start)


def _leading_indent_width(raw: str) -> int:
    """Count leading whitespace characters (spaces/tabs as-is)."""
    count = 0
    for char in raw:
        if char in " \t":
            count += 1
        else:
            break
    return count
