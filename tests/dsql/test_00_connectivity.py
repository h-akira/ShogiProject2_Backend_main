"""Phase 1: DSQL connectivity tests.

Verifies that the connection to Aurora DSQL is established and basic queries work.
"""
from __future__ import annotations


class TestConnectivity:
  def test_connect_to_dsql(self, dsql_conn):
    """Connection object is valid and not closed."""
    assert dsql_conn is not None
    assert not dsql_conn.closed

  def test_execute_select_1(self, dsql_conn):
    """Basic SELECT 1 query works."""
    with dsql_conn.cursor() as cur:
      cur.execute("SELECT 1 AS result")
      row = cur.fetchone()
    dsql_conn.commit()
    assert row["result"] == 1

  def test_current_database(self, dsql_conn):
    """Aurora DSQL database name is always 'postgres'."""
    with dsql_conn.cursor() as cur:
      cur.execute("SELECT current_database() AS db")
      row = cur.fetchone()
    dsql_conn.commit()
    assert row["db"] == "postgres"

  def test_version_check(self, dsql_conn):
    """Server version indicates PostgreSQL 16 compatibility."""
    with dsql_conn.cursor() as cur:
      cur.execute("SHOW server_version")
      row = cur.fetchone()
    dsql_conn.commit()
    version = row["server_version"]
    assert version.startswith("16"), f"Expected PostgreSQL 16.x, got {version}"
