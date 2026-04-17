"""Datetime utility for generating ISO 8601 timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso8601() -> str:
  """Return the current UTC time as an ISO 8601 string."""
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
