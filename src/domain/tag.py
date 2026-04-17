"""Tag aggregate root.

The Tag entity represents a user-defined label for categorizing Kifus.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects import TagId, TagName, Username


@dataclass
class Tag:
  """Aggregate root for the Tag aggregate."""

  _tid: TagId
  _username: Username
  _name: TagName
  _created_at: str
  _updated_at: str

  # -- Properties --

  @property
  def tid(self) -> TagId:
    return self._tid

  @property
  def username(self) -> Username:
    return self._username

  @property
  def name(self) -> TagName:
    return self._name

  @property
  def created_at(self) -> str:
    return self._created_at

  @property
  def updated_at(self) -> str:
    return self._updated_at

  # -- Factory Methods --

  @classmethod
  def create(
    cls,
    tid: TagId,
    username: Username,
    name: TagName,
    now: str,
  ) -> Tag:
    """Create a new Tag entity."""
    return cls(
      _tid=tid,
      _username=username,
      _name=name,
      _created_at=now,
      _updated_at=now,
    )

  @classmethod
  def reconstitute(
    cls,
    tid: TagId,
    username: Username,
    name: TagName,
    created_at: str,
    updated_at: str,
  ) -> Tag:
    """Rebuild a Tag entity from persisted data."""
    return cls(
      _tid=tid,
      _username=username,
      _name=name,
      _created_at=created_at,
      _updated_at=updated_at,
    )

  # -- Command Methods --

  def rename(self, new_name: TagName, now: str) -> None:
    """Rename the tag."""
    self._name = new_name
    self._updated_at = now
