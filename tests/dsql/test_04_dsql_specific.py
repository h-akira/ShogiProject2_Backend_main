"""Phase 4: DSQL-specific behavior tests.

Verifies Aurora DSQL-specific behaviors that differ from standard PostgreSQL.
"""
from __future__ import annotations

from tests.dsql.conftest import TEST_USERNAME


class TestTransaction:
  def test_transaction_commit(self, dsql_conn):
    """Data persists after explicit commit."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_tx0100001", TEST_USERNAME, "Commit Tag"),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s",
        ("dt_tx0100001",),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is not None
    assert row["name"] == "Commit Tag"

  def test_transaction_rollback(self, dsql_conn):
    """Data is discarded after rollback."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_tx0200001", TEST_USERNAME, "Rollback Tag"),
      )
    dsql_conn.rollback()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s",
        ("dt_tx0200001",),
      )
      row = cur.fetchone()
    dsql_conn.commit()

    assert row is None

  def test_multiple_dml_in_transaction(self, dsql_conn):
    """Multiple DML statements in a single transaction."""
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_tx0300001", TEST_USERNAME, "Multi DML 1"),
      )
      cur.execute(
        """
        INSERT INTO tags (tid, username, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        ("dt_tx0400001", TEST_USERNAME, "Multi DML 2"),
      )
      cur.execute(
        """
        UPDATE tags SET name = %s, updated_at = NOW()
        WHERE tid = %s AND username = %s
        """,
        ("Multi DML Updated", "dt_tx0300001", TEST_USERNAME),
      )
    dsql_conn.commit()

    with dsql_conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE username = %s AND tid LIKE 'dt_tx03%%' OR tid LIKE 'dt_tx04%%' ORDER BY tid",
        (TEST_USERNAME,),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    assert len(rows) == 2
    assert rows[0]["name"] == "Multi DML Updated"
    assert rows[1]["name"] == "Multi DML 2"


class TestDsqlFunctions:
  def test_now_function(self, dsql_conn):
    """NOW() returns timezone-aware timestamp."""
    with dsql_conn.cursor() as cur:
      cur.execute("SELECT NOW() AS ts")
      row = cur.fetchone()
    dsql_conn.commit()

    ts = row["ts"]
    assert ts is not None
    assert ts.tzinfo is not None

  def test_collation_c(self, dsql_conn):
    """String sorting uses C collation (byte order)."""
    tags = [
      ("dt_coll00001", "banana"),
      ("dt_coll00002", "Apple"),
      ("dt_coll00003", "cherry"),
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
        "SELECT name FROM tags WHERE username = %s AND tid LIKE 'dt_coll%%' ORDER BY name",
        (TEST_USERNAME,),
      )
      rows = cur.fetchall()
    dsql_conn.commit()

    names = [r["name"] for r in rows]
    # C collation: uppercase letters come before lowercase
    assert names == ["Apple", "banana", "cherry"]
