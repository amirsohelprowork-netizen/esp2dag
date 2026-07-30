"""Source location and application extraction models.

These types are shared across extractor, lexer, parser, and diagnostics.
They intentionally contain no ESP grammar knowledge beyond application boundaries.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SourceSpan(BaseModel):
    """Inclusive source range (1-based line/column) for traceability and diagnostics."""

    model_config = ConfigDict(frozen=True)

    file: str
    start_line: int = Field(ge=1)
    start_column: int = Field(default=1, ge=1)
    end_line: int = Field(ge=1)
    end_column: int = Field(default=1, ge=1)
    text: str | None = None


class SourceTrace(BaseModel):
    """Mandatory provenance attached to every generated task / IR element."""

    model_config = ConfigDict(frozen=True)

    source_file: str
    source_application: str
    source_job: str | None = None
    source_line: int = Field(ge=1)
    source_column: int | None = Field(default=None, ge=1)
    source_statement: str | None = None

    @classmethod
    def from_span(
        cls,
        *,
        application: str,
        job: str | None,
        span: SourceSpan,
    ) -> SourceTrace:
        """Build a trace from a span and naming context."""
        return cls(
            source_file=span.file,
            source_application=application,
            source_job=job,
            source_line=span.start_line,
            source_column=span.start_column,
            source_statement=span.text,
        )


class SourceFile(BaseModel):
    """In-memory source file loaded for compilation."""

    model_config = ConfigDict(frozen=True)

    path: Path
    content: str
    encoding: str = "utf-8"

    @property
    def path_str(self) -> str:
        """Normalized path string for spans and reports."""
        return str(self.path)


class SourceApplication(BaseModel):
    """One ESP application sliced from a schedule file.

    Produced by Phase 1 (Application Extractor). Does not contain parsed jobs.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    source_file: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str
    header_line: str | None = None

    @property
    def span(self) -> SourceSpan:
        """Span covering the entire application block."""
        return SourceSpan(
            file=self.source_file,
            start_line=self.start_line,
            start_column=1,
            end_line=self.end_line,
            end_column=1,
            text=self.header_line,
        )
