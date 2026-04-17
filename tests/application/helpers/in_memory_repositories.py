"""In-memory repository implementations for testing.

These implement the domain Repository ABCs using simple dict storage,
allowing application-layer tests to run without any database.
"""

from __future__ import annotations

from domain.exceptions import ConflictError
from domain.kifu import Kifu
from domain.repositories import KifuRepository, TagRepository
from domain.tag import Tag
from domain.value_objects import KifuId, ShareCode, TagId, Username


class InMemoryKifuRepository(KifuRepository):
  """Dict-based in-memory implementation of KifuRepository."""

  def __init__(self) -> None:
    self._store: dict[str, Kifu] = {}
    self._tag_associations: dict[str, set[str]] = {}  # kid -> set of tid
    self._tag_names: dict[str, str] = {}  # tid -> name (set externally)

  def set_tag_name(self, tid: str, name: str) -> None:
    """Test helper: register a tag name for response building."""
    self._tag_names[tid] = name

  def find_by_id(self, username: Username, kid: KifuId) -> Kifu | None:
    kifu = self._store.get(kid.value)
    if kifu and kifu.username == username:
      return kifu
    return None

  def find_by_id_with_tags(
    self, username: Username, kid: KifuId
  ) -> Kifu | None:
    return self.find_by_id(username, kid)

  def find_recent(
    self, username: Username, limit: int = 10
  ) -> tuple[list[Kifu], int]:
    user_kifus = [
      k for k in self._store.values() if k.username == username
    ]
    user_kifus.sort(key=lambda k: k.updated_at, reverse=True)
    total = len(user_kifus)
    return user_kifus[:limit], total

  def find_by_slug_prefix(
    self, username: Username, prefix: str
  ) -> list[Kifu]:
    normalized = prefix if not prefix or prefix.endswith("/") else prefix + "/"
    return [
      k
      for k in self._store.values()
      if k.username == username
      and (not normalized or k.slug.value.startswith(normalized))
    ]

  def find_by_share_code(self, share_code: ShareCode) -> Kifu | None:
    for kifu in self._store.values():
      if (
        kifu.shared
        and kifu.share_code is not None
        and kifu.share_code == share_code
      ):
        return kifu
    return None

  def count(self, username: Username) -> int:
    return sum(
      1 for k in self._store.values() if k.username == username
    )

  def save(self, kifu: Kifu) -> Kifu:
    # Simulate UNIQUE constraint on (username, slug)
    for existing in self._store.values():
      if (
        existing.username == kifu.username
        and existing.slug == kifu.slug
        and existing.kid != kifu.kid
      ):
        raise ConflictError(f"slug '{kifu.slug.value}' already exists")
    self._store[kifu.kid.value] = kifu
    return kifu

  def save_tag_associations(
    self, kid: KifuId, to_add: set[TagId], to_remove: set[TagId]
  ) -> None:
    current = self._tag_associations.get(kid.value, set())
    current -= {t.value for t in to_remove}
    current |= {t.value for t in to_add}
    self._tag_associations[kid.value] = current

  def delete(self, kifu: Kifu) -> None:
    self._store.pop(kifu.kid.value, None)
    self._tag_associations.pop(kifu.kid.value, None)

  def delete_all_for_user(self, username: Username) -> None:
    kids_to_delete = [
      kid
      for kid, k in self._store.items()
      if k.username == username
    ]
    for kid in kids_to_delete:
      del self._store[kid]
      self._tag_associations.pop(kid, None)

  def get_tag_ids_for_kifu(self, kid: KifuId) -> set[TagId]:
    raw = self._tag_associations.get(kid.value, set())
    return {TagId(tid) for tid in raw}

  def get_tag_names_for_kifu(self, kid: KifuId) -> list[dict]:
    raw = self._tag_associations.get(kid.value, set())
    return [
      {"tid": tid, "name": self._tag_names.get(tid, tid)}
      for tid in sorted(raw)
    ]


class InMemoryTagRepository(TagRepository):
  """Dict-based in-memory implementation of TagRepository."""

  def __init__(self) -> None:
    self._store: dict[str, Tag] = {}
    self._kifu_associations: dict[str, list[dict]] = {}  # tid -> kifu summaries

  def set_kifu_association(
    self, tid: str, kifus: list[dict]
  ) -> None:
    """Test helper: set kifu associations for a tag."""
    self._kifu_associations[tid] = kifus

  def find_by_id(self, username: Username, tid: TagId) -> Tag | None:
    tag = self._store.get(tid.value)
    if tag and tag.username == username:
      return tag
    return None

  def find_all(self, username: Username) -> list[Tag]:
    tags = [
      t for t in self._store.values() if t.username == username
    ]
    tags.sort(key=lambda t: t.name.value)
    return tags

  def count(self, username: Username) -> int:
    return sum(
      1 for t in self._store.values() if t.username == username
    )

  def check_exist(
    self, username: Username, tag_ids: list[TagId]
  ) -> list[TagId]:
    return [
      tid
      for tid in tag_ids
      if tid.value in self._store
      and self._store[tid.value].username == username
    ]

  def save(self, tag: Tag) -> Tag:
    # Simulate UNIQUE constraint on (username, name)
    for existing in self._store.values():
      if (
        existing.username == tag.username
        and existing.name == tag.name
        and existing.tid != tag.tid
      ):
        raise ConflictError(
          f"Tag name '{tag.name.value}' already exists"
        )
    self._store[tag.tid.value] = tag
    return tag

  def delete(self, tag: Tag) -> None:
    self._store.pop(tag.tid.value, None)
    self._kifu_associations.pop(tag.tid.value, None)

  def delete_all_for_user(self, username: Username) -> None:
    tids_to_delete = [
      tid
      for tid, t in self._store.items()
      if t.username == username
    ]
    for tid in tids_to_delete:
      del self._store[tid]
      self._kifu_associations.pop(tid, None)

  def find_kifus_by_tag(
    self, username: Username, tid: TagId
  ) -> list[dict]:
    return self._kifu_associations.get(tid.value, [])
