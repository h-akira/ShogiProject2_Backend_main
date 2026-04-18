"""Tests for domain value objects."""

import pytest

from domain.exceptions import DomainValidationError
from domain.value_objects import (
  GameResult,
  KifuId,
  ShareCode,
  Side,
  Slug,
  TagId,
  TagName,
  Username,
)


class TestKifuId:
  def test_valid_creation(self):
    kid = KifuId("abcdef123456")
    assert kid.value == "abcdef123456"

  def test_equality(self):
    assert KifuId("abcdef123456") == KifuId("abcdef123456")

  def test_inequality(self):
    assert KifuId("abcdef123456") != KifuId("abcdef123457")

  def test_empty_raises_error(self):
    with pytest.raises(DomainValidationError, match="12 characters"):
      KifuId("")

  def test_too_short_raises_error(self):
    with pytest.raises(DomainValidationError, match="12 characters"):
      KifuId("abc")

  def test_too_long_raises_error(self):
    with pytest.raises(DomainValidationError, match="12 characters"):
      KifuId("abcdef1234567")

  def test_non_alphanumeric_raises_error(self):
    with pytest.raises(DomainValidationError, match="alphanumeric"):
      KifuId("abcdef12345!")

  def test_immutable(self):
    kid = KifuId("abcdef123456")
    with pytest.raises(AttributeError):
      kid.value = "other"


class TestTagId:
  def test_valid_creation_12_chars(self):
    tid = TagId("abcdef123456")
    assert tid.value == "abcdef123456"

  def test_valid_creation_8_chars(self):
    """Legacy tags use 8-char IDs."""
    tid = TagId("uPPh3pHj")
    assert tid.value == "uPPh3pHj"

  def test_empty_raises_error(self):
    with pytest.raises(DomainValidationError):
      TagId("")

  def test_too_short_raises_error(self):
    with pytest.raises(DomainValidationError):
      TagId("abc")

  def test_too_long_raises_error(self):
    with pytest.raises(DomainValidationError):
      TagId("a" * 13)


class TestSlug:
  def test_valid_creation_with_kif(self):
    slug = Slug("year/2024/game.kif")
    assert slug.value == "year/2024/game.kif"

  def test_auto_appends_kif(self):
    slug = Slug("year/2024/game")
    assert slug.value == "year/2024/game.kif"

  def test_does_not_double_append_kif(self):
    slug = Slug("game.kif")
    assert slug.value == "game.kif"

  def test_equality_after_normalization(self):
    assert Slug("game") == Slug("game.kif")

  def test_empty_raises_error(self):
    with pytest.raises(DomainValidationError, match="1-255"):
      Slug("")

  def test_leading_slash_raises_error(self):
    with pytest.raises(DomainValidationError, match="must not start with"):
      Slug("/invalid/path")

  def test_max_length_without_kif(self):
    # 251 chars + ".kif" = 255, should pass
    slug = Slug("a" * 251)
    assert len(slug.value) == 255

  def test_too_long_after_normalization(self):
    # 252 chars + ".kif" = 256, should fail
    with pytest.raises(DomainValidationError, match="1-255"):
      Slug("a" * 252)

  def test_max_length_with_kif(self):
    # 255 chars ending in .kif, should pass
    slug = Slug("a" * 251 + ".kif")
    assert len(slug.value) == 255

  def test_immutable(self):
    slug = Slug("game.kif")
    with pytest.raises(AttributeError):
      slug.value = "other"


class TestSide:
  def test_all_values(self):
    assert Side.NONE.value == "none"
    assert Side.SENTE.value == "sente"
    assert Side.GOTE.value == "gote"

  def test_from_string(self):
    assert Side("sente") == Side.SENTE

  def test_invalid_value(self):
    with pytest.raises(ValueError):
      Side("invalid")


class TestGameResult:
  def test_all_values(self):
    assert GameResult.NONE.value == "none"
    assert GameResult.WIN.value == "win"
    assert GameResult.LOSS.value == "loss"
    assert GameResult.SENNICHITE.value == "sennichite"
    assert GameResult.JISHOGI.value == "jishogi"

  def test_from_string(self):
    assert GameResult("sennichite") == GameResult.SENNICHITE

  def test_invalid_value(self):
    with pytest.raises(ValueError):
      GameResult("draw")


class TestShareCode:
  def test_valid_creation(self):
    code = ShareCode("a" * 36)
    assert code.value == "a" * 36

  def test_wrong_length_raises_error(self):
    with pytest.raises(DomainValidationError, match="36 characters"):
      ShareCode("abc")

  def test_non_alphanumeric_raises_error(self):
    with pytest.raises(DomainValidationError, match="alphanumeric"):
      ShareCode("a" * 35 + "!")


class TestTagName:
  def test_valid_creation(self):
    name = TagName("opening")
    assert name.value == "opening"

  def test_empty_raises_error(self):
    with pytest.raises(DomainValidationError, match="1-127"):
      TagName("")

  def test_too_long_raises_error(self):
    with pytest.raises(DomainValidationError, match="1-127"):
      TagName("a" * 128)

  def test_max_length(self):
    name = TagName("a" * 127)
    assert len(name.value) == 127


class TestUsername:
  def test_valid_creation(self):
    username = Username("testuser")
    assert username.value == "testuser"

  def test_empty_raises_error(self):
    with pytest.raises(DomainValidationError, match="must not be empty"):
      Username("")
