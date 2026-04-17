"""Repository interfaces (Abstract Base Classes).

These interfaces define the contract for data persistence.
Implementations live in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.kifu import Kifu
from domain.tag import Tag
from domain.value_objects import KifuId, ShareCode, TagId, Username


class KifuRepository(ABC):
  """Abstract repository for Kifu aggregate persistence."""

  @abstractmethod
  def find_by_id(self, username: Username, kid: KifuId) -> Kifu | None:
    """Find a kifu by username and kid (without tag names)."""
    ...

  @abstractmethod
  def find_by_id_with_tags(self, username: Username, kid: KifuId) -> Kifu | None:
    """Find a kifu by username and kid (with tag_ids populated)."""
    ...

  @abstractmethod
  def find_recent(
    self, username: Username, limit: int = 10
  ) -> tuple[list[Kifu], int]:
    """Find recently updated kifus and total count."""
    ...

  @abstractmethod
  def find_by_slug_prefix(self, username: Username, prefix: str) -> list[Kifu]:
    """Find kifus whose slug starts with the given prefix."""
    ...

  @abstractmethod
  def find_by_share_code(self, share_code: ShareCode) -> Kifu | None:
    """Find a shared kifu by share_code."""
    ...

  @abstractmethod
  def count(self, username: Username) -> int:
    """Count total kifus for a user."""
    ...

  @abstractmethod
  def save(self, kifu: Kifu) -> Kifu:
    """Insert or update a kifu."""
    ...

  @abstractmethod
  def save_tag_associations(
    self, kid: KifuId, to_add: set[TagId], to_remove: set[TagId]
  ) -> None:
    """Add and remove tag associations for a kifu."""
    ...

  @abstractmethod
  def delete(self, kifu: Kifu) -> None:
    """Delete a kifu and its tag associations."""
    ...

  @abstractmethod
  def delete_all_for_user(self, username: Username) -> None:
    """Delete all kifus and kifu_tags for a user (account deletion)."""
    ...

  @abstractmethod
  def get_tag_ids_for_kifu(self, kid: KifuId) -> set[TagId]:
    """Get all tag IDs associated with a kifu."""
    ...

  @abstractmethod
  def get_tag_names_for_kifu(
    self, kid: KifuId
  ) -> list[dict]:
    """Get tag id-name pairs for a kifu (for response building)."""
    ...


class TagRepository(ABC):
  """Abstract repository for Tag aggregate persistence."""

  @abstractmethod
  def find_by_id(self, username: Username, tid: TagId) -> Tag | None:
    """Find a tag by username and tid."""
    ...

  @abstractmethod
  def find_all(self, username: Username) -> list[Tag]:
    """Find all tags for a user, sorted by name."""
    ...

  @abstractmethod
  def count(self, username: Username) -> int:
    """Count total tags for a user."""
    ...

  @abstractmethod
  def check_exist(
    self, username: Username, tag_ids: list[TagId]
  ) -> list[TagId]:
    """Check which of the given tag_ids exist. Returns existing IDs."""
    ...

  @abstractmethod
  def save(self, tag: Tag) -> Tag:
    """Insert or update a tag."""
    ...

  @abstractmethod
  def delete(self, tag: Tag) -> None:
    """Delete a tag and its kifu associations."""
    ...

  @abstractmethod
  def delete_all_for_user(self, username: Username) -> None:
    """Delete all tags for a user (account deletion)."""
    ...

  @abstractmethod
  def find_kifus_by_tag(
    self, username: Username, tid: TagId
  ) -> list[dict]:
    """Find kifu summaries associated with a tag.

    Returns list of dicts with: kid, slug, created_at, updated_at.
    """
    ...
