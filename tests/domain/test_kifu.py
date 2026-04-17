"""Tests for Kifu aggregate root."""

import pytest

from domain.exceptions import DomainValidationError
from domain.kifu import Kifu
from domain.value_objects import (
  GameResult,
  KifuId,
  ShareCode,
  Side,
  Slug,
  TagId,
  Username,
)


def _make_kid() -> KifuId:
  return KifuId("abcdef123456")


def _make_username() -> Username:
  return Username("testuser")


def _make_share_code() -> ShareCode:
  return ShareCode("a" * 36)


def _make_kifu(**overrides) -> Kifu:
  defaults = {
    "kid": _make_kid(),
    "username": _make_username(),
    "slug": Slug("year/2024/game.kif"),
    "side": Side.SENTE,
    "result": GameResult.WIN,
    "memo": "test memo",
    "kif": "some kif data",
    "shared": False,
    "share_code": None,
    "tag_ids": set(),
    "now": "2024-01-01T00:00:00Z",
  }
  defaults.update(overrides)
  return Kifu.create(**defaults)


class TestKifuCreate:
  def test_success(self):
    kifu = _make_kifu()
    assert kifu.kid == _make_kid()
    assert kifu.username == _make_username()
    assert kifu.slug == Slug("year/2024/game.kif")
    assert kifu.side == Side.SENTE
    assert kifu.result == GameResult.WIN
    assert kifu.memo == "test memo"
    assert kifu.kif == "some kif data"
    assert kifu.shared is False
    assert kifu.share_code is None
    assert kifu.tag_ids == frozenset()
    assert kifu.created_at == "2024-01-01T00:00:00Z"
    assert kifu.updated_at == "2024-01-01T00:00:00Z"

  def test_with_shared(self):
    code = _make_share_code()
    kifu = _make_kifu(shared=True, share_code=code)
    assert kifu.shared is True
    assert kifu.share_code == code

  def test_with_tags(self):
    tag_ids = {TagId("tag111111111"), TagId("tag222222222")}
    kifu = _make_kifu(tag_ids=tag_ids)
    assert kifu.tag_ids == frozenset(tag_ids)

  def test_empty_kif_raises_error(self):
    with pytest.raises(DomainValidationError, match="kif is required"):
      _make_kifu(kif="")

  def test_shared_without_share_code_raises_error(self):
    with pytest.raises(DomainValidationError, match="share_code is required"):
      _make_kifu(shared=True, share_code=None)

  def test_not_shared_clears_share_code(self):
    kifu = _make_kifu(shared=False, share_code=_make_share_code())
    assert kifu.share_code is None


class TestKifuReconstitute:
  def test_rebuilds_from_persisted_data(self):
    kifu = Kifu.reconstitute(
      kid=_make_kid(),
      username=_make_username(),
      slug=Slug("game.kif"),
      side=Side.NONE,
      result=GameResult.NONE,
      memo="",
      kif="data",
      shared=False,
      share_code=None,
      tag_ids=set(),
      created_at="2024-01-01T00:00:00Z",
      updated_at="2024-06-01T00:00:00Z",
    )
    assert kifu.created_at == "2024-01-01T00:00:00Z"
    assert kifu.updated_at == "2024-06-01T00:00:00Z"


class TestKifuUpdate:
  def test_update_fields(self):
    kifu = _make_kifu()
    kifu.update(
      slug=Slug("new/path.kif"),
      side=Side.GOTE,
      result=GameResult.LOSS,
      memo="updated memo",
      kif="updated kif",
      shared=False,
      share_code=None,
      now="2024-06-01T00:00:00Z",
    )
    assert kifu.slug == Slug("new/path.kif")
    assert kifu.side == Side.GOTE
    assert kifu.result == GameResult.LOSS
    assert kifu.memo == "updated memo"
    assert kifu.kif == "updated kif"
    assert kifu.updated_at == "2024-06-01T00:00:00Z"

  def test_update_enable_sharing(self):
    kifu = _make_kifu()
    code = _make_share_code()
    kifu.update(
      slug=kifu.slug,
      side=kifu.side,
      result=kifu.result,
      memo=kifu.memo,
      kif=kifu.kif,
      shared=True,
      share_code=code,
      now="2024-06-01T00:00:00Z",
    )
    assert kifu.shared is True
    assert kifu.share_code == code

  def test_update_disable_sharing(self):
    kifu = _make_kifu(shared=True, share_code=_make_share_code())
    kifu.update(
      slug=kifu.slug,
      side=kifu.side,
      result=kifu.result,
      memo=kifu.memo,
      kif=kifu.kif,
      shared=False,
      share_code=None,
      now="2024-06-01T00:00:00Z",
    )
    assert kifu.shared is False
    assert kifu.share_code is None

  def test_update_empty_kif_raises_error(self):
    kifu = _make_kifu()
    with pytest.raises(DomainValidationError, match="kif is required"):
      kifu.update(
        slug=kifu.slug,
        side=kifu.side,
        result=kifu.result,
        memo=kifu.memo,
        kif="",
        shared=False,
        share_code=None,
        now="2024-06-01T00:00:00Z",
      )


class TestKifuRegenerateShareCode:
  def test_regenerates_code(self):
    kifu = _make_kifu(shared=True, share_code=_make_share_code())
    new_code = ShareCode("b" * 36)
    kifu.regenerate_share_code(new_code, "2024-06-01T00:00:00Z")
    assert kifu.share_code == new_code
    assert kifu.updated_at == "2024-06-01T00:00:00Z"


class TestKifuTagChanges:
  def test_compute_tag_changes(self):
    tag1 = TagId("tag111111111")
    tag2 = TagId("tag222222222")
    tag3 = TagId("tag333333333")
    kifu = _make_kifu(tag_ids={tag1, tag2})

    to_add, to_remove = kifu.compute_tag_changes({tag2, tag3})
    assert to_add == {tag3}
    assert to_remove == {tag1}

  def test_compute_tag_changes_no_diff(self):
    tag1 = TagId("tag111111111")
    kifu = _make_kifu(tag_ids={tag1})

    to_add, to_remove = kifu.compute_tag_changes({tag1})
    assert to_add == set()
    assert to_remove == set()

  def test_apply_tag_changes(self):
    tag1 = TagId("tag111111111")
    tag2 = TagId("tag222222222")
    kifu = _make_kifu(tag_ids={tag1})

    kifu.apply_tag_changes({tag2})
    assert kifu.tag_ids == frozenset({tag2})
