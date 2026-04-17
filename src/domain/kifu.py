"""Kifu aggregate root.

The Kifu entity represents a shogi game record with metadata,
sharing capability, and tag associations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.exceptions import DomainValidationError
from domain.value_objects import (
  GameResult,
  KifuId,
  ShareCode,
  Side,
  Slug,
  TagId,
  Username,
)


@dataclass
class Kifu:
  """Aggregate root for the Kifu aggregate.

  External code should use the create() factory method for new instances
  and the reconstitute() class method for rebuilding from persistence.
  """

  _kid: KifuId
  _username: Username
  _slug: Slug
  _side: Side
  _result: GameResult
  _memo: str
  _kif: str
  _shared: bool
  _share_code: ShareCode | None
  _tag_ids: set[TagId]
  _created_at: str
  _updated_at: str

  # -- Properties --

  @property
  def kid(self) -> KifuId:
    return self._kid

  @property
  def username(self) -> Username:
    return self._username

  @property
  def slug(self) -> Slug:
    return self._slug

  @property
  def side(self) -> Side:
    return self._side

  @property
  def result(self) -> GameResult:
    return self._result

  @property
  def memo(self) -> str:
    return self._memo

  @property
  def kif(self) -> str:
    return self._kif

  @property
  def shared(self) -> bool:
    return self._shared

  @property
  def share_code(self) -> ShareCode | None:
    return self._share_code

  @property
  def tag_ids(self) -> frozenset[TagId]:
    return frozenset(self._tag_ids)

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
    kid: KifuId,
    username: Username,
    slug: Slug,
    side: Side,
    result: GameResult,
    memo: str,
    kif: str,
    shared: bool,
    share_code: ShareCode | None,
    tag_ids: set[TagId],
    now: str,
  ) -> Kifu:
    """Create a new Kifu entity with full validation."""
    if not kif:
      raise DomainValidationError("kif is required")

    # Enforce share_code invariant
    if shared and share_code is None:
      raise DomainValidationError("share_code is required when shared is true")
    if not shared:
      share_code = None

    return cls(
      _kid=kid,
      _username=username,
      _slug=slug,
      _side=side,
      _result=result,
      _memo=memo,
      _kif=kif,
      _shared=shared,
      _share_code=share_code,
      _tag_ids=set(tag_ids),
      _created_at=now,
      _updated_at=now,
    )

  @classmethod
  def reconstitute(
    cls,
    kid: KifuId,
    username: Username,
    slug: Slug,
    side: Side,
    result: GameResult,
    memo: str,
    kif: str,
    shared: bool,
    share_code: ShareCode | None,
    tag_ids: set[TagId],
    created_at: str,
    updated_at: str,
  ) -> Kifu:
    """Rebuild a Kifu entity from persisted data (no validation)."""
    return cls(
      _kid=kid,
      _username=username,
      _slug=slug,
      _side=side,
      _result=result,
      _memo=memo,
      _kif=kif,
      _shared=shared,
      _share_code=share_code,
      _tag_ids=set(tag_ids),
      _created_at=created_at,
      _updated_at=updated_at,
    )

  # -- Command Methods --

  def update(
    self,
    slug: Slug,
    side: Side,
    result: GameResult,
    memo: str,
    kif: str,
    shared: bool,
    share_code: ShareCode | None,
    now: str,
  ) -> None:
    """Update kifu metadata."""
    if not kif:
      raise DomainValidationError("kif is required")

    if shared and share_code is None:
      raise DomainValidationError("share_code is required when shared is true")
    if not shared:
      share_code = None

    self._slug = slug
    self._side = side
    self._result = result
    self._memo = memo
    self._kif = kif
    self._shared = shared
    self._share_code = share_code
    self._updated_at = now

  def regenerate_share_code(self, new_code: ShareCode, now: str) -> None:
    """Regenerate the share code."""
    self._share_code = new_code
    self._updated_at = now

  def compute_tag_changes(
    self, new_tag_ids: set[TagId]
  ) -> tuple[set[TagId], set[TagId]]:
    """Compute tag association diff.

    Returns:
        (to_add, to_remove) tuple of TagId sets.
    """
    to_add = new_tag_ids - self._tag_ids
    to_remove = self._tag_ids - new_tag_ids
    return to_add, to_remove

  def apply_tag_changes(self, new_tag_ids: set[TagId]) -> None:
    """Replace tag associations entirely."""
    self._tag_ids = set(new_tag_ids)
