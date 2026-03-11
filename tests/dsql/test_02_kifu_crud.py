"""Phase 3: Kifu CRUD tests on DSQL.

Verifies that kifu repository SQL operations work correctly on Aurora DSQL.
"""
from __future__ import annotations

import pytest
import psycopg.errors

from tests.dsql.conftest import TEST_USERNAME


class TestKifuInsertAndGet:
  def test_insert_kifu(self, dsql_conn):
    """INSERT with RETURNING * works on DSQL."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, share_code, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING *
        """,
        ("dt_k01000001", TEST_USERNAME, "dsql_test/game1.kif", "sente", "win", "test memo", "test kif data", False, None),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row["kid"] == "dt_k01000001"
    assert row["username"] == TEST_USERNAME
    assert row["slug"] == "dsql_test/game1.kif"
    assert row["side"] == "sente"
    assert row["result"] == "win"
    assert row["created_at"] is not None
    assert row["updated_at"] is not None

  def test_get_kifu(self, dsql_conn):
    """SELECT by kid and username returns the correct row."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        ("dt_k02000001", TEST_USERNAME, "dsql_test/game2.kif", "gote", "loss", "", "kif data", False),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE kid = %s AND username = %s",
        ("dt_k02000001", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is not None
    assert row["slug"] == "dsql_test/game2.kif"
    assert row["side"] == "gote"

  def test_get_kifu_not_found(self, dsql_conn):
    """SELECT for non-existent kid returns None."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE kid = %s AND username = %s",
        ("dt_knotfound", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is None


class TestKifuListAndQuery:
  def _insert_kifus(self, dsql_conn):
    """Insert multiple kifus for list/query tests."""
    kifus = [
      ("dt_k10000001", "dsql_test/folder/a.kif", "2025-01-01T00:00:00Z"),
      ("dt_k11000001", "dsql_test/folder/b.kif", "2025-01-02T00:00:00Z"),
      ("dt_k12000001", "dsql_test/other.kif", "2025-01-03T00:00:00Z"),
    ]
    for kid, slug, updated_at in kifus:
      with dsql_conn.cursor() as cur:
        cur.execute(
          """
          INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
          VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, %s, %s)
          """,
          (kid, TEST_USERNAME, slug, updated_at, updated_at),
        )
      dsql_conn.commit()

  def test_list_recent_kifus(self, dsql_conn):
    """ORDER BY updated_at DESC with COUNT(*) OVER() works."""
    self._insert_kifus(dsql_conn)

    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        SELECT *, COUNT(*) OVER() AS total_count
        FROM kifus
        WHERE username = %s
        ORDER BY updated_at DESC
        LIMIT 10
        """,
        (TEST_USERNAME,),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    assert len(rows) == 3
    assert rows[0]["total_count"] == 3
    assert rows[0]["kid"] == "dt_k12000001"

  def test_query_by_slug_prefix(self, dsql_conn):
    """LIKE prefix search works on DSQL."""
    self._insert_kifus(dsql_conn)

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT kid, slug FROM kifus WHERE username = %s AND slug LIKE %s ORDER BY slug",
        (TEST_USERNAME, "dsql_test/folder/%"),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    assert len(rows) == 2
    assert all(r["slug"].startswith("dsql_test/folder/") for r in rows)


class TestKifuUpdate:
  def test_update_kifu(self, dsql_conn):
    """UPDATE with RETURNING * works on DSQL."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
        VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, NOW(), NOW())
        """,
        ("dt_k20000001", TEST_USERNAME, "dsql_test/update.kif"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        UPDATE kifus
        SET slug = %s, memo = %s, updated_at = NOW()
        WHERE kid = %s AND username = %s
        RETURNING *
        """,
        ("dsql_test/updated.kif", "updated memo", "dt_k20000001", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row["slug"] == "dsql_test/updated.kif"
    assert row["memo"] == "updated memo"


class TestKifuUniqueConstraint:
  def test_slug_unique_constraint(self, dsql_conn):
    """Duplicate slug for same user raises UniqueViolation."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
        VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, NOW(), NOW())
        """,
        ("dt_k30000001", TEST_USERNAME, "dsql_test/unique.kif"),
      )
    dsql_conn.commit()

    with pytest.raises(psycopg.errors.UniqueViolation):
      with dsql_conn.cursor() as cur:
        cur.execute(
          """
          INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
          VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, NOW(), NOW())
          """,
          ("dt_k31000001", TEST_USERNAME, "dsql_test/unique.kif"),
        )
      dsql_conn.commit()
    dsql_conn.rollback()


class TestKifuShared:
  def test_shared_kifu(self, dsql_conn):
    """Query by share_code works."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, share_code, created_at, updated_at)
        VALUES (%s, %s, %s, 'sente', 'win', 'memo', 'kif data', TRUE, %s, NOW(), NOW())
        """,
        ("dt_k40000001", TEST_USERNAME, "dsql_test/shared.kif", "dt_sc_001"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE share_code = %s AND shared = TRUE",
        ("dt_sc_001",),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is not None
    assert row["kid"] == "dt_k40000001"


class TestKifuDelete:
  def test_delete_kifu(self, dsql_conn):
    """DELETE removes the row."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
        VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, NOW(), NOW())
        """,
        ("dt_k50000001", TEST_USERNAME, "dsql_test/delete.kif"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "DELETE FROM kifus WHERE kid = %s AND username = %s",
        ("dt_k50000001", TEST_USERNAME),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE kid = %s AND username = %s",
        ("dt_k50000001", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is None
