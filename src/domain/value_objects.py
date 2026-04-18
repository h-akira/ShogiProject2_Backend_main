"""Value Objects for the KifuManagement bounded context.

All Value Objects are immutable (frozen dataclass) and validate
their invariants at creation time. Invalid values raise
DomainValidationError.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.exceptions import DomainValidationError


class Side(Enum):
  """Player's side in a game."""
  NONE = "none"
  SENTE = "sente"
  GOTE = "gote"


class GameResult(Enum):
  """Result of a game."""
  NONE = "none"
  WIN = "win"
  LOSS = "loss"
  SENNICHITE = "sennichite"
  JISHOGI = "jishogi"


@dataclass(frozen=True)
class KifuId:
  """Unique identifier for a Kifu entity (12-char alphanumeric)."""
  value: str

  def __post_init__(self) -> None:
    if not self.value or len(self.value) != 12:
      raise DomainValidationError("KifuId must be exactly 12 characters")
    if not self.value.isalnum():
      raise DomainValidationError("KifuId must be alphanumeric")


@dataclass(frozen=True)
class TagId:
  """Unique identifier for a Tag entity (8-12 char alphanumeric).

  Legacy tags use 8-char IDs; new tags use 12-char IDs.
  """
  value: str

  def __post_init__(self) -> None:
    if not self.value or not (8 <= len(self.value) <= 12):
      raise DomainValidationError("TagId must be 8-12 characters")
    if not self.value.isalnum():
      raise DomainValidationError("TagId must be alphanumeric")


@dataclass(frozen=True)
class Slug:
  """Hierarchical path for a Kifu (e.g., year/2024/January/game.kif).

  Automatically appends '.kif' extension if not present.
  """
  value: str

  def __post_init__(self) -> None:
    if not self.value:
      raise DomainValidationError("slug must be 1-255 characters")
    # Normalize: auto-append .kif
    normalized = self.value if self.value.endswith(".kif") else self.value + ".kif"
    if len(normalized) > 255:
      raise DomainValidationError("slug must be 1-255 characters")
    if normalized.startswith("/"):
      raise DomainValidationError("slug must not start with '/'")
    # Use object.__setattr__ because dataclass is frozen
    object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class ShareCode:
  """Random code for public access to a shared Kifu (36-char alphanumeric)."""
  value: str

  def __post_init__(self) -> None:
    if not self.value or len(self.value) != 36:
      raise DomainValidationError("ShareCode must be exactly 36 characters")
    if not self.value.isalnum():
      raise DomainValidationError("ShareCode must be alphanumeric")


@dataclass(frozen=True)
class TagName:
  """Display name for a Tag (1-127 characters)."""
  value: str

  def __post_init__(self) -> None:
    if not self.value or len(self.value) > 127:
      raise DomainValidationError("Tag name must be 1-127 characters")


@dataclass(frozen=True)
class Username:
  """User identifier from Cognito."""
  value: str

  def __post_init__(self) -> None:
    if not self.value:
      raise DomainValidationError("Username must not be empty")
