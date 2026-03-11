"""Repository layer tests.

These tests require a local PostgreSQL instance (via pytest-postgresql).
They are skipped if PostgreSQL is not available.
"""
from __future__ import annotations

import pytest

from tests.local.conftest import requires_postgresql


@requires_postgresql
class TestKifuRepository:
  def test_insert_and_get_kifu(self, db_connection):
    from repositories import kifu_repository

    kifu = kifu_repository.insert_kifu({
      "kid": "test12345678",
      "username": "testuser",
      "slug": "game1.kif",
      "side": "sente",
      "result": "win",
      "memo": "test memo",
      "kif": "test kif data",
      "shared": False,
      "share_code": None,
      "created_at": "2025-01-15T09:30:00Z",
      "updated_at": "2025-01-15T09:30:00Z",
    })
    assert kifu["kid"] == "test12345678"

    fetched = kifu_repository.get_kifu("testuser", "test12345678")
    assert fetched is not None
    assert fetched["slug"] == "game1.kif"
    assert fetched["side"] == "sente"

  def test_get_kifu_not_found(self, db_connection):
    from repositories import kifu_repository

    result = kifu_repository.get_kifu("testuser", "nonexistent1")
    assert result is None

  def test_list_kifus_by_latest_update(self, db_connection):
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_older001",
      "username": "testuser",
      "slug": "old.kif",
      "kif": "data",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z",
    })
    kifu_repository.insert_kifu({
      "kid": "kid_newer001",
      "username": "testuser",
      "slug": "new.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    results = kifu_repository.list_recent_kifus("testuser")
    assert len(results) == 2
    assert results[0]["kid"] == "kid_newer001"

  def test_count_kifus(self, db_connection):
    from repositories import kifu_repository

    assert kifu_repository.count_kifus("testuser") == 0

    kifu_repository.insert_kifu({
      "kid": "kid_count001",
      "username": "testuser",
      "slug": "count.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    assert kifu_repository.count_kifus("testuser") == 1

  def test_slug_unique_constraint(self, db_connection):
    import psycopg.errors
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_slug0001",
      "username": "testuser",
      "slug": "unique.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    with pytest.raises(psycopg.errors.UniqueViolation):
      kifu_repository.insert_kifu({
        "kid": "kid_slug0002",
        "username": "testuser",
        "slug": "unique.kif",
        "kif": "data",
        "created_at": "2025-01-15T00:00:00Z",
        "updated_at": "2025-01-15T00:00:00Z",
      })
    db_connection.rollback()

  def test_update_kifu(self, db_connection):
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_upd00001",
      "username": "testuser",
      "slug": "original.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    updated = kifu_repository.update_kifu("kid_upd00001", "testuser", {
      "slug": "updated.kif",
      "memo": "updated memo",
    })
    assert updated["slug"] == "updated.kif"
    assert updated["memo"] == "updated memo"

  def test_delete_kifu(self, db_connection):
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_del00001",
      "username": "testuser",
      "slug": "delete.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    kifu_repository.delete_kifu("kid_del00001", "testuser")
    assert kifu_repository.get_kifu("testuser", "kid_del00001") is None

  def test_query_by_slug_prefix(self, db_connection):
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_pfx00001",
      "username": "testuser",
      "slug": "folder/game1.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu({
      "kid": "kid_pfx00002",
      "username": "testuser",
      "slug": "folder/game2.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu({
      "kid": "kid_pfx00003",
      "username": "testuser",
      "slug": "other.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    results = kifu_repository.query_by_slug_prefix("testuser", "folder/")
    assert len(results) == 2

  def test_query_shared_kifu(self, db_connection):
    from repositories import kifu_repository

    kifu_repository.insert_kifu({
      "kid": "kid_shr00001",
      "username": "testuser",
      "slug": "shared.kif",
      "kif": "data",
      "shared": True,
      "share_code": "abc123def456",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    result = kifu_repository.get_shared_kifu("abc123def456")
    assert result is not None
    assert result["kid"] == "kid_shr00001"

  def test_query_shared_kifu_not_found(self, db_connection):
    from repositories import kifu_repository

    result = kifu_repository.get_shared_kifu("nonexistent_code")
    assert result is None

  def test_insert_and_get_tag_associations(self, db_connection):
    from repositories import kifu_repository, tag_repository

    kifu_repository.insert_kifu({
      "kid": "kid_tag00001",
      "username": "testuser",
      "slug": "tagged.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    tag_repository.insert_tag({
      "tid": "tid_tag00001",
      "username": "testuser",
      "name": "tag1",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    kifu_repository.insert_kifu_tags("kid_tag00001", ["tid_tag00001"])

    tag_ids = kifu_repository.get_tag_ids_for_kifu("kid_tag00001")
    assert "tid_tag00001" in tag_ids

  def test_get_kifu_with_tags(self, db_connection):
    from repositories import kifu_repository, tag_repository

    kifu_repository.insert_kifu({
      "kid": "kid_wtag0001",
      "username": "testuser",
      "slug": "with_tags.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    tag_repository.insert_tag({
      "tid": "tid_wtag0001",
      "username": "testuser",
      "name": "testtag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu_tags("kid_wtag0001", ["tid_wtag0001"])

    result = kifu_repository.get_kifu_with_tags("testuser", "kid_wtag0001")
    assert result is not None
    assert len(result["tags"]) == 1
    assert result["tags"][0]["name"] == "testtag"

  def test_delete_tag_associations(self, db_connection):
    from repositories import kifu_repository, tag_repository

    kifu_repository.insert_kifu({
      "kid": "kid_dtag0001",
      "username": "testuser",
      "slug": "del_tags.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    tag_repository.insert_tag({
      "tid": "tid_dtag0001",
      "username": "testuser",
      "name": "deltag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu_tags("kid_dtag0001", ["tid_dtag0001"])

    kifu_repository.delete_kifu_tags("kid_dtag0001", ["tid_dtag0001"])
    tag_ids = kifu_repository.get_tag_ids_for_kifu("kid_dtag0001")
    assert len(tag_ids) == 0


@requires_postgresql
class TestTagRepository:
  def test_insert_and_get_tag(self, db_connection):
    from repositories import tag_repository

    tag = tag_repository.insert_tag({
      "tid": "tid_ins00001",
      "username": "testuser",
      "name": "Test Tag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    assert tag["tid"] == "tid_ins00001"

    fetched = tag_repository.get_tag("testuser", "tid_ins00001")
    assert fetched is not None
    assert fetched["name"] == "Test Tag"

  def test_get_tag_not_found(self, db_connection):
    from repositories import tag_repository

    result = tag_repository.get_tag("testuser", "nonexistent1")
    assert result is None

  def test_list_tags(self, db_connection):
    from repositories import tag_repository

    tag_repository.insert_tag({
      "tid": "tid_lst00001",
      "username": "testuser",
      "name": "B Tag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    tag_repository.insert_tag({
      "tid": "tid_lst00002",
      "username": "testuser",
      "name": "A Tag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    tags = tag_repository.list_tags("testuser")
    assert len(tags) == 2
    assert tags[0]["name"] == "A Tag"

  def test_count_tags(self, db_connection):
    from repositories import tag_repository

    assert tag_repository.count_tags("testuser") == 0

    tag_repository.insert_tag({
      "tid": "tid_cnt00001",
      "username": "testuser",
      "name": "Count Tag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    assert tag_repository.count_tags("testuser") == 1

  def test_tag_name_unique_constraint(self, db_connection):
    import psycopg.errors
    from repositories import tag_repository

    tag_repository.insert_tag({
      "tid": "tid_unq00001",
      "username": "testuser",
      "name": "Unique",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    with pytest.raises(psycopg.errors.UniqueViolation):
      tag_repository.insert_tag({
        "tid": "tid_unq00002",
        "username": "testuser",
        "name": "Unique",
        "created_at": "2025-01-15T00:00:00Z",
        "updated_at": "2025-01-15T00:00:00Z",
      })
    db_connection.rollback()

  def test_update_tag(self, db_connection):
    from repositories import tag_repository

    tag_repository.insert_tag({
      "tid": "tid_upd00001",
      "username": "testuser",
      "name": "Original",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    updated = tag_repository.update_tag("tid_upd00001", "testuser", {
      "name": "Updated",
    })
    assert updated["name"] == "Updated"

  def test_delete_tag(self, db_connection):
    from repositories import tag_repository

    tag_repository.insert_tag({
      "tid": "tid_del00001",
      "username": "testuser",
      "name": "Delete Me",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })

    tag_repository.delete_tag("tid_del00001", "testuser")
    assert tag_repository.get_tag("testuser", "tid_del00001") is None

  def test_get_kifus_by_tag(self, db_connection):
    from repositories import kifu_repository, tag_repository

    tag_repository.insert_tag({
      "tid": "tid_kbt00001",
      "username": "testuser",
      "name": "Kifu Tag",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu({
      "kid": "kid_kbt00001",
      "username": "testuser",
      "slug": "tag_kifu.kif",
      "kif": "data",
      "created_at": "2025-01-15T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z",
    })
    kifu_repository.insert_kifu_tags("kid_kbt00001", ["tid_kbt00001"])

    kifus = tag_repository.get_kifus_by_tag("testuser", "tid_kbt00001")
    assert len(kifus) == 1
    assert kifus[0]["kid"] == "kid_kbt00001"
