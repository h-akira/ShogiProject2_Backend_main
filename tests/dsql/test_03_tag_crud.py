"""Phase 3: Tag CRUD tests on DSQL.

Verifies that tag repository SQL operations work correctly on Aurora DSQL.
"""
from __future__ import annotations

import pytest
import psycopg.errors

from tests.dsql.conftest import TEST_USERNAME


class TestTagInsertAndGet:
  def test_insert_tag(self, dsql_conn):
    """INSERT with RETURNING * works on DSQL."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        RETURNING *
        """,
        ("dt_t01000001", TEST_USERNAME, "Test Tag"),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row["tid"] == "dt_t01000001"
    assert row["name"] == "Test Tag"

  def test_get_tag(self, dsql_conn):
    """SELECT by tid and username returns the correct row."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_t02000001", TEST_USERNAME, "Get Tag"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s AND username = %s",
        ("dt_t02000001", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is not None
    assert row["name"] == "Get Tag"

  def test_get_tag_not_found(self, dsql_conn):
    """SELECT for non-existent tid returns None."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s AND username = %s",
        ("dt_tnotfound", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is None


class TestTagList:
  def test_list_tags(self, dsql_conn):
    """ORDER BY name returns tags sorted alphabetically."""
    tags = [
      ("dt_t10000001", "B Tag"),
      ("dt_t11000001", "A Tag"),
      ("dt_t12000001", "C Tag"),
    ]
    for tid, name in tags:
      with dsql_conn.cursor() as cur:
        cur.execute(
          """
          INSERT INTO tags (tid, username, name, created_at, updated_at)
          VALUES (%s, %s, %s, NOW(), NOW())
          """,
          (tid, TEST_USERNAME, name),
        )
      dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE username = %s ORDER BY name",
        (TEST_USERNAME,),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    assert len(rows) == 3
    assert rows[0]["name"] == "A Tag"
    assert rows[1]["name"] == "B Tag"
    assert rows[2]["name"] == "C Tag"


class TestTagUniqueConstraint:
  def test_tag_name_unique_constraint(self, dsql_conn):
    """Duplicate tag name for same user raises UniqueViolation."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_t20000001", TEST_USERNAME, "Unique Tag"),
      )
    dsql_conn.commit()

    with pytest.raises(psycopg.errors.UniqueViolation):
      with dsql_conn.cursor() as cur:
        cur.execute(
          """
          INSERT INTO tags (tid, username, name, created_at, updated_at)
          VALUES (%s, %s, %s, NOW(), NOW())
          """,
          ("dt_t21000001", TEST_USERNAME, "Unique Tag"),
        )
      dsql_conn.commit()
    dsql_conn.rollback()


class TestKifuTagAssociation:
  def _setup_kifu_and_tag(self, dsql_conn):
    """Insert a kifu and a tag for association tests."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, created_at, updated_at)
        VALUES (%s, %s, %s, 'none', 'none', '', 'data', FALSE, NOW(), NOW())
        """,
        ("dt_k60000001", TEST_USERNAME, "dsql_test/tagged.kif"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_t30000001", TEST_USERNAME, "Assoc Tag"),
      )
    dsql_conn.commit()

  def test_insert_kifu_tags(self, dsql_conn):
    """INSERT into kifu_tags creates the association."""
    self._setup_kifu_and_tag(dsql_conn)

    with dsql_conn.cursor() as cur:
      cur.execute(
        "INSERT INTO kifu_tags (kid, tid) VALUES (%s, %s)",
        ("dt_k60000001", "dt_t30000001"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT tid FROM kifu_tags WHERE kid = %s",
        ("dt_k60000001",),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    assert len(rows) == 1
    assert rows[0]["tid"] == "dt_t30000001"

  def test_get_kifu_with_tags(self, dsql_conn):
    """LEFT JOIN with json_agg returns kifu with tags."""
    self._setup_kifu_and_tag(dsql_conn)

    with dsql_conn.cursor() as cur:
      cur.execute(
        "INSERT INTO kifu_tags (kid, tid) VALUES (%s, %s)",
        ("dt_k60000001", "dt_t30000001"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        SELECT k.*,
               COALESCE(
                 json_agg(json_build_object('tid', t.tid, 'name', t.name))
                 FILTER (WHERE t.tid IS NOT NULL),
                 '[]'::json
               ) AS tags
        FROM kifus k
        LEFT JOIN kifu_tags kt ON k.kid = kt.kid
        LEFT JOIN tags t ON kt.tid = t.tid
        WHERE k.kid = %s AND k.username = %s
        GROUP BY k.kid
        """,
        ("dt_k60000001", TEST_USERNAME),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is not None
    assert len(row["tags"]) == 1
    assert row["tags"][0]["name"] == "Assoc Tag"

  def test_delete_tag_cascades_kifu_tags(self, dsql_conn):
    """Deleting kifu_tags then tag removes the association."""
    self._setup_kifu_and_tag(dsql_conn)

    with dsql_conn.cursor() as cur:
      cur.execute(
        "INSERT INTO kifu_tags (kid, tid) VALUES (%s, %s)",
        ("dt_k60000001", "dt_t30000001"),
      )
    dsql_conn.commit()

    # Delete kifu_tags first (no CASCADE in DSQL), then tag
    with dsql_conn.cursor() as cur:
      cur.execute(
        "DELETE FROM kifu_tags WHERE tid = %s",
        ("dt_t30000001",),
      )
      cur.execute(
        "DELETE FROM tags WHERE tid = %s AND username = %s",
        ("dt_t30000001", TEST_USERNAME),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifu_tags WHERE tid = %s",
        ("dt_t30000001",),
      )
      kt_rows = cur.fetchall()
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s",
        ("dt_t30000001",),
      )
      t_row = cur.fetchone()
    dsql_conn.commit()

    assert len(kt_rows) == 0
    assert t_row is None
