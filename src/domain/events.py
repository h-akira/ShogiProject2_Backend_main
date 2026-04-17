"""Domain events (placeholder for future use).

Domain events represent important business facts that have occurred.
Currently this module is a placeholder — events can be added when
cross-aggregate or cross-context communication is needed.

Example future events:
  - KifuCreated: triggered when a new kifu is created
  - KifuShared: triggered when a kifu is shared publicly
  - AccountDeleted: triggered when a user deletes their account
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
  """Base class for domain events."""
  pass
