"""Service layer tests.

Uses unittest.mock to mock repository functions, so PostgreSQL is not required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from common.exceptions import (
  ConflictError,
  LimitExceededError,
  NotFoundError,
  ValidationError,
)


class TestKifuService:
  def test_create_kifu_success(self):
    from services import kifu_service

    with (
      patch.object(kifu_service, "kifu_repository") as mock_kr,
      patch.object(kifu_service, "tag_repository") as mock_tr,
      patch.object(kifu_service, "generate_id", return_value="kid_test0001"),
      patch.object(kifu_service, "generate_share_code", return_value="sc_test001"),
      patch.object(kifu_service, "now_iso8601", return_value="2025-01-15T09:30:00Z"),
    ):
      mock_kr.count_kifus.return_value = 0
      mock_kr.insert_kifu.return_value = {
        "kid": "kid_test0001",
        "username": "testuser",
        "slug": "game1.kif",
        "side": "sente",
        "result": "win",
        "memo": "memo",
        "kif": "kif data",
        "shared": False,
        "share_code": None,
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      result = kifu_service.create_kifu("testuser", {
        "slug": "game1",
        "side": "sente",
        "result": "win",
        "memo": "memo",
        "kif": "kif data",
      })

      assert result["kid"] == "kid_test0001"
      assert result["slug"] == "game1.kif"
      mock_kr.insert_kifu.assert_called_once()

  def test_create_kifu_with_tags(self):
    from services import kifu_service

    with (
      patch.object(kifu_service, "kifu_repository") as mock_kr,
      patch.object(kifu_service, "tag_repository") as mock_tr,
      patch.object(kifu_service, "generate_id", return_value="kid_tag00001"),
      patch.object(kifu_service, "now_iso8601", return_value="2025-01-15T09:30:00Z"),
    ):
      mock_kr.count_kifus.return_value = 0
      mock_tr.check_tags_exist.return_value = ["tid1"]
      mock_kr.insert_kifu.return_value = {
        "kid": "kid_tag00001",
        "username": "testuser",
        "slug": "game.kif",
        "side": "none",
        "result": "none",
        "memo": "",
        "kif": "data",
        "shared": False,
        "share_code": None,
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }
      mock_tr.get_tag.return_value = {"tid": "tid1", "name": "tag1"}

      result = kifu_service.create_kifu("testuser", {
        "slug": "game",
        "side": "none",
        "result": "none",
        "kif": "data",
        "tag_ids": ["tid1"],
      })

      mock_kr.insert_kifu_tags.assert_called_once_with("kid_tag00001", ["tid1"])
      assert result["tags"] == [{"tid": "tid1", "name": "tag1"}]

  def test_create_kifu_invalid_slug(self):
    from services import kifu_service

    with pytest.raises(ValidationError):
      kifu_service.create_kifu("testuser", {
        "slug": "",
        "side": "none",
        "result": "none",
        "kif": "data",
      })

  def test_create_kifu_slug_starts_with_slash(self):
    from services import kifu_service

    with pytest.raises(ValidationError, match="must not start with"):
      kifu_service.create_kifu("testuser", {
        "slug": "/game",
        "side": "none",
        "result": "none",
        "kif": "data",
      })

  def test_create_kifu_invalid_side(self):
    from services import kifu_service

    with pytest.raises(ValidationError, match="side"):
      kifu_service.create_kifu("testuser", {
        "slug": "game",
        "side": "invalid",
        "result": "none",
        "kif": "data",
      })

  def test_create_kifu_invalid_result(self):
    from services import kifu_service

    with pytest.raises(ValidationError, match="result"):
      kifu_service.create_kifu("testuser", {
        "slug": "game",
        "side": "none",
        "result": "invalid",
        "kif": "data",
      })

  def test_create_kifu_empty_kif(self):
    from services import kifu_service

    with pytest.raises(ValidationError, match="kif is required"):
      kifu_service.create_kifu("testuser", {
        "slug": "game",
        "side": "none",
        "result": "none",
        "kif": "",
      })

  def test_create_kifu_limit_exceeded(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.count_kifus.return_value = 2000

      with pytest.raises(LimitExceededError):
        kifu_service.create_kifu("testuser", {
          "slug": "game",
          "side": "none",
          "result": "none",
          "kif": "data",
        })

  def test_create_kifu_slug_conflict(self):
    import psycopg.errors
    from services import kifu_service

    with (
      patch.object(kifu_service, "kifu_repository") as mock_kr,
      patch.object(kifu_service, "generate_id", return_value="kid_conf0001"),
      patch.object(kifu_service, "now_iso8601", return_value="2025-01-15T09:30:00Z"),
      patch("repositories.db.get_connection") as mock_get_conn,
    ):
      mock_kr.count_kifus.return_value = 0
      mock_kr.insert_kifu.side_effect = psycopg.errors.UniqueViolation()
      mock_get_conn.return_value = MagicMock()
      with pytest.raises(ConflictError):
        kifu_service.create_kifu("testuser", {
          "slug": "game",
          "side": "none",
          "result": "none",
          "kif": "data",
        })

  def test_get_kifu_success(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_kifu_with_tags.return_value = {
        "kid": "kid_get00001",
        "slug": "game.kif",
        "side": "sente",
        "result": "win",
        "tags": [{"tid": "t1", "name": "tag1"}],
        "memo": "",
        "shared": False,
        "share_code": None,
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      result = kifu_service.get_kifu("testuser", "kid_get00001")
      assert result["kid"] == "kid_get00001"
      assert result["tags"] == [{"tid": "t1", "name": "tag1"}]

  def test_get_kifu_not_found(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_kifu_with_tags.return_value = None

      with pytest.raises(NotFoundError):
        kifu_service.get_kifu("testuser", "nonexistent")

  def test_get_recent_kifus(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.list_recent_kifus.return_value = [
        {
          "kid": "k1",
          "slug": "g1.kif",
          "side": "none",
          "result": "none",
          "tags": [],
          "updated_at": "2025-01-15T09:30:00Z",
          "total_count": 5,
        },
      ]

      result = kifu_service.get_recent_kifus("testuser")
      assert result["total_count"] == 5
      assert len(result["kifus"]) == 1

  def test_update_kifu_success(self):
    from services import kifu_service

    with (
      patch.object(kifu_service, "kifu_repository") as mock_kr,
      patch.object(kifu_service, "now_iso8601", return_value="2025-01-15T10:00:00Z"),
    ):
      mock_kr.get_kifu.return_value = {
        "kid": "kid_upd00001",
        "slug": "old.kif",
        "shared": False,
        "share_code": None,
      }
      mock_kr.update_kifu.return_value = {
        "kid": "kid_upd00001",
        "slug": "new.kif",
        "side": "gote",
        "result": "loss",
        "memo": "",
        "kif": "data",
        "shared": False,
        "share_code": None,
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
      }
      mock_kr.get_kifu_with_tags.return_value = {
        "kid": "kid_upd00001",
        "slug": "new.kif",
        "side": "gote",
        "result": "loss",
        "tags": [],
        "memo": "",
        "kif": "data",
        "shared": False,
        "share_code": None,
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
      }

      result = kifu_service.update_kifu("testuser", "kid_upd00001", {
        "slug": "new",
        "side": "gote",
        "result": "loss",
        "kif": "data",
      })
      assert result["slug"] == "new.kif"

  def test_update_kifu_not_found(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_kifu.return_value = None

      with pytest.raises(NotFoundError):
        kifu_service.update_kifu("testuser", "nonexistent", {
          "slug": "game",
          "side": "none",
          "result": "none",
          "kif": "data",
        })

  def test_delete_kifu_success(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_kifu.return_value = {"kid": "kid_del00001"}

      kifu_service.delete_kifu("testuser", "kid_del00001")
      mock_kr.delete_kifu.assert_called_once_with("kid_del00001", "testuser")

  def test_delete_kifu_not_found(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_kifu.return_value = None

      with pytest.raises(NotFoundError):
        kifu_service.delete_kifu("testuser", "nonexistent")

  def test_get_explorer_root(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.query_by_slug_prefix.return_value = [
        {"kid": "k1", "slug": "game1.kif"},
        {"kid": "k2", "slug": "folder/game2.kif"},
        {"kid": "k3", "slug": "folder/game3.kif"},
      ]

      result = kifu_service.get_explorer("testuser", "")
      assert result["path"] == ""
      assert len(result["files"]) == 1
      assert result["files"][0]["name"] == "game1.kif"
      assert len(result["folders"]) == 1
      assert result["folders"][0]["name"] == "folder"
      assert result["folders"][0]["count"] == 2

  def test_get_explorer_subfolder(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.query_by_slug_prefix.return_value = [
        {"kid": "k1", "slug": "folder/game1.kif"},
        {"kid": "k2", "slug": "folder/sub/game2.kif"},
      ]

      result = kifu_service.get_explorer("testuser", "folder")
      assert result["path"] == "folder"
      assert len(result["files"]) == 1
      assert len(result["folders"]) == 1

  def test_get_shared_kifu_success(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_shared_kifu.return_value = {
        "slug": "shared.kif",
        "side": "sente",
        "result": "win",
        "memo": "memo",
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      result = kifu_service.get_shared_kifu("sharecode123")
      assert result["slug"] == "shared.kif"

  def test_get_shared_kifu_not_found(self):
    from services import kifu_service

    with patch.object(kifu_service, "kifu_repository") as mock_kr:
      mock_kr.get_shared_kifu.return_value = None

      with pytest.raises(NotFoundError):
        kifu_service.get_shared_kifu("nonexistent")

  def test_regenerate_share_code(self):
    from services import kifu_service

    with (
      patch.object(kifu_service, "kifu_repository") as mock_kr,
      patch.object(kifu_service, "generate_share_code", return_value="new_share_code_123"),
      patch.object(kifu_service, "now_iso8601", return_value="2025-01-15T10:00:00Z"),
    ):
      mock_kr.get_kifu.return_value = {"kid": "kid_rsc00001"}

      result = kifu_service.regenerate_share_code("testuser", "kid_rsc00001")
      assert result["share_code"] == "new_share_code_123"

  def test_normalize_slug_adds_kif(self):
    from services.kifu_service import _normalize_slug

    assert _normalize_slug("game") == "game.kif"
    assert _normalize_slug("game.kif") == "game.kif"
    assert _normalize_slug("folder/game") == "folder/game.kif"


class TestTagService:
  def test_create_tag_success(self):
    from services import tag_service

    with (
      patch.object(tag_service, "tag_repository") as mock_tr,
      patch.object(tag_service, "generate_id", return_value="tid_test0001"),
      patch.object(tag_service, "now_iso8601", return_value="2025-01-15T09:30:00Z"),
    ):
      mock_tr.count_tags.return_value = 0
      mock_tr.insert_tag.return_value = {
        "tid": "tid_test0001",
        "name": "Test Tag",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      result = tag_service.create_tag("testuser", {"name": "Test Tag"})
      assert result["tid"] == "tid_test0001"
      assert result["name"] == "Test Tag"

  def test_create_tag_name_conflict(self):
    import psycopg.errors
    from services import tag_service

    with (
      patch.object(tag_service, "tag_repository") as mock_tr,
      patch.object(tag_service, "generate_id", return_value="tid_conf0001"),
      patch.object(tag_service, "now_iso8601", return_value="2025-01-15T09:30:00Z"),
      patch("repositories.db.get_connection") as mock_get_conn,
    ):
      mock_tr.count_tags.return_value = 0
      mock_tr.insert_tag.side_effect = psycopg.errors.UniqueViolation()
      mock_get_conn.return_value = MagicMock()
      with pytest.raises(ConflictError):
        tag_service.create_tag("testuser", {"name": "Duplicate"})

  def test_create_tag_limit_exceeded(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.count_tags.return_value = 50

      with pytest.raises(LimitExceededError):
        tag_service.create_tag("testuser", {"name": "New Tag"})

  def test_create_tag_invalid_name_empty(self):
    from services import tag_service

    with pytest.raises(ValidationError):
      tag_service.create_tag("testuser", {"name": ""})

  def test_create_tag_invalid_name_too_long(self):
    from services import tag_service

    with pytest.raises(ValidationError):
      tag_service.create_tag("testuser", {"name": "a" * 128})

  def test_get_tags(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.list_tags.return_value = [
        {"tid": "t1", "name": "Tag A", "created_at": "2025-01-15T09:30:00Z", "updated_at": "2025-01-15T09:30:00Z"},
        {"tid": "t2", "name": "Tag B", "created_at": "2025-01-15T09:30:00Z", "updated_at": "2025-01-15T09:30:00Z"},
      ]

      result = tag_service.get_tags("testuser")
      assert len(result) == 2

  def test_get_tag_with_kifus(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.get_tag.return_value = {
        "tid": "t1",
        "name": "Tag",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }
      mock_tr.get_kifus_by_tag.return_value = [
        {"kid": "k1", "slug": "g1.kif", "created_at": "2025-01-15T09:30:00Z", "updated_at": "2025-01-15T09:30:00Z"},
      ]

      result = tag_service.get_tag("testuser", "t1")
      assert result["tid"] == "t1"
      assert len(result["kifus"]) == 1

  def test_get_tag_not_found(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.get_tag.return_value = None

      with pytest.raises(NotFoundError):
        tag_service.get_tag("testuser", "nonexistent")

  def test_update_tag_success(self):
    from services import tag_service

    with (
      patch.object(tag_service, "tag_repository") as mock_tr,
      patch.object(tag_service, "now_iso8601", return_value="2025-01-15T10:00:00Z"),
    ):
      mock_tr.get_tag.return_value = {
        "tid": "t1",
        "name": "Old",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }
      mock_tr.update_tag.return_value = {
        "tid": "t1",
        "name": "New",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
      }

      result = tag_service.update_tag("testuser", "t1", {"name": "New"})
      assert result["name"] == "New"

  def test_update_tag_not_found(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.get_tag.return_value = None

      with pytest.raises(NotFoundError):
        tag_service.update_tag("testuser", "nonexistent", {"name": "New"})

  def test_delete_tag_success(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.get_tag.return_value = {"tid": "t1"}

      tag_service.delete_tag("testuser", "t1")
      mock_tr.delete_tag.assert_called_once_with("t1", "testuser")

  def test_delete_tag_not_found(self):
    from services import tag_service

    with patch.object(tag_service, "tag_repository") as mock_tr:
      mock_tr.get_tag.return_value = None

      with pytest.raises(NotFoundError):
        tag_service.delete_tag("testuser", "nonexistent")
