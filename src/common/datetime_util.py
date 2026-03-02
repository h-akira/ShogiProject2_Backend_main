from datetime import datetime, timezone


def now_iso8601() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
