"""Phase 2: Schema verification tests.

Verifies that migrations have been applied correctly.
"""
from __future__ import annotations

import pytest


EXPECTED_KIFUS_COLUMNS = {
  "kid": "character varying",
  "username": "character varying",
  "slug": "character varying",
  "side": "character varying",
  "result": "character varying",
  "memo": "text",
  "kif": "text",
  "shared": "boolean",
  "share_code": "character varying",
  "created_at": "timestamp with time zone",
  "updated_at": "timestamp with time zone",
}

EXPECTED_TAGS_COLUMNS = {
  "tid": "character varying",
  "username": "character varying",
  "name": "character varying",
  "created_at": "timestamp with time zone",
  "updated_at": "timestamp with time zone",
}

EXPECTED_KIFU_TAGS_COLUMNS = {
  "kid": "character varying",
  "tid": "character varying",
}

EXPECTED_INDEXES = [
  "idx_kifus_user_updated",
  "idx_kifus_user_slug",
  "idx_kifus_share_code",
  "idx_tags_user_name",
  "idx_kifu_tags_tid",
]


def _get_columns(conn, table_name: str) -> dict[str, str]:
  """Get column names and data types for a table."""
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = %s
      ORDER BY ordinal_position
      """,
      (table_name,),
    )
    rows = cur.fetchall()
  conn.commit()
  return {row["column_name"]: row["data_type"] for row in rows}


def _table_exists(conn, table_name: str) -> bool:
  """Check if a table exists in the public schema."""
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
      ) AS exists
      """,
      (table_name,),
    )
    row = cur.fetchone()
  conn.commit()
  return row["exists"]


class TestTableExists:
  def test_kifus_table_exists(self, dsql_conn):
    assert _table_exists(dsql_conn, "kifus")

  def test_tags_table_exists(self, dsql_conn):
    assert _table_exists(dsql_conn, "tags")

  def test_kifu_tags_table_exists(self, dsql_conn):
    assert _table_exists(dsql_conn, "kifu_tags")


class TestTableColumns:
  def test_kifus_columns(self, dsql_conn):
    columns = _get_columns(dsql_conn, "kifus")
    for col_name, col_type in EXPECTED_KIFUS_COLUMNS.items():
      assert col_name in columns, f"Missing column: {col_name}"
      assert columns[col_name] == col_type, (
        f"Column {col_name}: expected {col_type}, got {columns[col_name]}"
      )

  def test_tags_columns(self, dsql_conn):
    columns = _get_columns(dsql_conn, "tags")
    for col_name, col_type in EXPECTED_TAGS_COLUMNS.items():
      assert col_name in columns, f"Missing column: {col_name}"
      assert columns[col_name] == col_type, (
        f"Column {col_name}: expected {col_type}, got {columns[col_name]}"
      )

  def test_kifu_tags_columns(self, dsql_conn):
    columns = _get_columns(dsql_conn, "kifu_tags")
    for col_name, col_type in EXPECTED_KIFU_TAGS_COLUMNS.items():
      assert col_name in columns, f"Missing column: {col_name}"
      assert columns[col_name] == col_type, (
        f"Column {col_name}: expected {col_type}, got {columns[col_name]}"
      )


class TestIndexes:
  def test_indexes_exist(self, dsql_conn):
    with dsql_conn.cursor() as cur:
      cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        """,
      )
      rows = cur.fetchall()
    dsql_conn.commit()
    existing_indexes = {row["indexname"] for row in rows}

    for idx_name in EXPECTED_INDEXES:
      assert idx_name in existing_indexes, f"Missing index: {idx_name}"
