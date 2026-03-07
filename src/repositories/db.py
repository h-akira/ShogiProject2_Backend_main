from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from common.config import DSQL_CLUSTER_ENDPOINT

_conn: psycopg.Connection | None = None


def get_connection() -> psycopg.Connection:
  global _conn
  if _conn is None or _conn.closed:
    from aurora_dsql_psycopg import DSQLConnection
    _conn = DSQLConnection.connect(
      DSQL_CLUSTER_ENDPOINT,
      autocommit=False,
      row_factory=dict_row,
    )
  return _conn
