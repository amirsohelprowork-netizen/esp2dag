"""Load SourceApplication units from a schedule or extract artifact."""

from __future__ import annotations

import re
from pathlib import Path

from esp2dag.extractor import ApplicationExtractor
from esp2dag.models.source import SourceApplication, SourceFile


def infer_base_line(filename: str) -> int | None:
    """Parse ``NAME__L2377.esp`` extract artifact filenames."""
    match = re.search(r"__L(\d+)\.esp$", filename, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def load_applications(
    path: Path,
    *,
    base_line: int | None = None,
    max_applications: int = 0,
) -> list[SourceApplication]:
    """Load one or more applications from a unit or schedule file."""
    content = path.read_text(encoding="utf-8", errors="replace")
    source = SourceFile(path=path.resolve(), content=content)
    extracted = ApplicationExtractor().extract(source).applications
    if not extracted:
        extracted = [
            SourceApplication(
                name=path.stem,
                source_file=str(path.resolve()),
                start_line=1,
                end_line=max(1, content.count("\n") + (0 if content.endswith("\n") else 1)),
                content=content,
                header_line=content.splitlines()[0] if content.strip() else None,
            )
        ]

    inferred = infer_base_line(path.name)
    offset = base_line if base_line is not None else inferred
    if offset is not None and len(extracted) == 1 and extracted[0].start_line == 1 and offset > 1:
        unit = extracted[0]
        shift = offset - 1
        extracted = [
            SourceApplication(
                name=unit.name,
                source_file=unit.source_file,
                start_line=unit.start_line + shift,
                end_line=unit.end_line + shift,
                content=unit.content,
                header_line=unit.header_line,
            )
        ]

    if max_applications > 0:
        extracted = extracted[:max_applications]
    return extracted
