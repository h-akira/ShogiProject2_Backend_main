"""Tests for Tag aggregate root."""

from domain.tag import Tag
from domain.value_objects import TagId, TagName, Username


def _make_tag(**overrides) -> Tag:
  defaults = {
    "tid": TagId("tag111111111"),
    "username": Username("testuser"),
    "name": TagName("opening"),
    "now": "2024-01-01T00:00:00Z",
  }
  defaults.update(overrides)
  return Tag.create(**defaults)


class TestTagCreate:
  def test_success(self):
    tag = _make_tag()
    assert tag.tid == TagId("tag111111111")
    assert tag.username == Username("testuser")
    assert tag.name == TagName("opening")
    assert tag.created_at == "2024-01-01T00:00:00Z"
    assert tag.updated_at == "2024-01-01T00:00:00Z"


class TestTagReconstitute:
  def test_rebuilds_from_persisted_data(self):
    tag = Tag.reconstitute(
      tid=TagId("tag111111111"),
      username=Username("testuser"),
      name=TagName("opening"),
      created_at="2024-01-01T00:00:00Z",
      updated_at="2024-06-01T00:00:00Z",
    )
    assert tag.created_at == "2024-01-01T00:00:00Z"
    assert tag.updated_at == "2024-06-01T00:00:00Z"


class TestTagRename:
  def test_rename_updates_name_and_timestamp(self):
    tag = _make_tag()
    tag.rename(TagName("endgame"), "2024-06-01T00:00:00Z")
    assert tag.name == TagName("endgame")
    assert tag.updated_at == "2024-06-01T00:00:00Z"
    assert tag.created_at == "2024-01-01T00:00:00Z"
