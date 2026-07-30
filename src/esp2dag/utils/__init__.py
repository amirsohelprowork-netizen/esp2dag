"""Shared utilities."""

from __future__ import annotations

import logging
import re


def configure_logging(level: int = logging.INFO) -> None:
    """Configure package-wide logging defaults for CLI usage."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


_UNSAFE_TASK_ID = re.compile(r"[^A-Za-z0-9_]+")


def sanitize_task_id(name: str) -> str:
    """Deterministically convert an ESP job name into an Airflow-safe task_id.

    Rules (stable contract for generators and tests):
    - Replace non [A-Za-z0-9_] runs with underscore
    - Strip leading/trailing underscores
    - If empty after sanitize, use ``task``
    - If starts with a digit, prefix ``t_``
    """
    cleaned = _UNSAFE_TASK_ID.sub("_", name).strip("_")
    if not cleaned:
        cleaned = "task"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned


def canonical_newline(text: str) -> str:
    """Normalize newlines to ``\\n`` for deterministic artifacts."""
    return text.replace("\r\n", "\n").replace("\r", "\n")
