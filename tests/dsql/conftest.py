"""DSQL integration test fixtures.

Connects to the deployed Aurora DSQL cluster for integration testing.
Requires AWS credentials (profile: shogi) and network access to the DSQL endpoint.
"""
from __future__ import annotations

import os

import pytest

DSQL_ENDPOINT = os.environ["DSQL_ENDPOINT"]
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
TEST_USERNAME = "dsql_test_user"
# kid/tid prefix: must fit within VARCHAR(12) → "dt_" + 9 chars
KID_PREFIX = "dt_"
TID_PREFIX = "dt_"


@pytest.fixture(scope="session")
def dsql_conn():
  """Session-scoped DSQL connection."""
  import aurora_dsql_psycopg as dsql
  from psycopg.rows import dict_row

  conn = dsql.connect(host=DSQL_ENDPOINT, dbname="postgres", region=REGION)
  conn.row_factory = dict_row
  yield conn
  conn.close()


@pytest.fixture(autouse=True)
def cleanup(dsql_conn):
  """Clean up test data after each test."""
  yield
  # Always rollback first to clear any failed transaction state
  try:
    dsql_conn.rollback()
  except Exception:
    pass
  try:
    with dsql_conn.cursor() as cur:
      cur.execute(
        "DELETE FROM kifu_tags WHERE kid LIKE %s", (KID_PREFIX + "%",)
      )
    dsql_conn.commit()
    with dsql_conn.cursor() as cur:
      cur.execute(
        "DELETE FROM kifus WHERE username = %s", (TEST_USERNAME,)
      )
    dsql_conn.commit()
    with dsql_conn.cursor() as cur:
      cur.execute(
        "DELETE FROM tags WHERE username = %s", (TEST_USERNAME,)
      )
    dsql_conn.commit()
  except Exception:
    dsql_conn.rollback()
