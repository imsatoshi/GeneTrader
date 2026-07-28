"""Timezone-aware time helpers.

The trading stack mixes three clocks: the Freqtrade API (UTC, ISO-8601 with an
offset), SQLite rows written by earlier versions (naive local time), and
``datetime.now()`` on the host (naive, local). Comparing an aware datetime with
a naive one raises TypeError, and comparing two naive datetimes from different
zones silently shifts every metrics window.

Everything in monitoring, scheduling, and deployment should use ``utc_now()``
and normalise values crossing a boundary with ``to_utc()``.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

UTC = timezone.utc


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def to_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Return ``value`` as aware UTC.

    Naive datetimes are assumed to already be UTC rather than local time: they
    come from data this system wrote itself (SQLite rows, JSON state files)
    before timestamps were made aware. Treating them as UTC keeps historical
    rows comparable instead of shifting them by the host's offset.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_utc(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string (with or without offset) into aware UTC."""
    if not value:
        return None
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        return to_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def utc_ago(**kwargs) -> datetime:
    """Aware UTC datetime for ``timedelta(**kwargs)`` before now."""
    return utc_now() - timedelta(**kwargs)


def utc_iso(value: Optional[datetime]) -> Optional[str]:
    """Canonical UTC string for storage and SQL range comparison.

    SQLite compares timestamps lexically, so every stored value must use one
    format. Offsets are stripped after conversion ("2026-07-29T02:00:00")
    rather than kept ("...+00:00"), which also keeps rows written before
    timestamps were made aware directly comparable.
    """
    normalised = to_utc(value)
    if normalised is None:
        return None
    return normalised.replace(tzinfo=None).isoformat()


__all__ = ['UTC', 'utc_now', 'to_utc', 'parse_utc', 'utc_ago', 'utc_iso']
