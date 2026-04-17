"""Database connection management for Aurora DSQL."""

from __future__ import annotations

from typing import Callable

import psycopg
from psycopg.rows import dict_row

from common.config import DSQL_CLUSTER_ENDPOINT

_conn: psycopg.Connection | None = None


def get_connection() -> psycopg.Connection:
  """Get or create a persistent database connection."""
  global _conn
  if _conn is None or _conn.closed:
    from aurora_dsql_psycopg import DSQLConnection
    _conn = DSQLConnection.connect(
      DSQL_CLUSTER_ENDPOINT,
      autocommit=True,
      row_factory=dict_row,
    )
  return _conn


# Type alias for dependency injection
ConnectionFactory = Callable[[], psycopg.Connection]
