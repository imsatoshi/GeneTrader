"""Path normalization helpers for offline data metadata outputs."""

from __future__ import annotations

from typing import Any


def normalize_offline_path_text(value: Any) -> str:
    """Return a stable slash-separated path string."""

    text = str(value or "").replace("\\", "/").strip()
    while "//" in text:
        text = text.replace("//", "/")
    return text


def normalize_offline_relative_path(value: Any) -> str:
    """Normalize a report dataset path without exposing a Windows drive prefix."""

    text = normalize_offline_path_text(value)
    if len(text) >= 2 and text[1] == ":":
        text = text[2:].lstrip("/")
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def offline_path_sort_key(value: Any) -> tuple[tuple[str, ...], str]:
    """Return a deterministic sort key that is stable across path separators."""

    normalized = normalize_offline_relative_path(value)
    return tuple(part.lower() for part in normalized.split("/")), normalized
