"""Framework-neutral normalization for form values."""

from __future__ import annotations


def normalize_priority(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None
