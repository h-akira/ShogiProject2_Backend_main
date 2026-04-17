"""PostgreSQL implementation of TagRepository."""

from __future__ import annotations

import psycopg.errors
from aws_lambda_powertools import Tracer

from domain.exceptions import ConflictError
from domain.repositories import TagRepository
from domain.tag import Tag
from domain.value_objects import TagId, TagName, Username
from infrastructure.db import ConnectionFactory

tracer = Tracer()


def _format_datetime(dt) -> str:
  """Convert DB datetime to ISO 8601 string."""
  if dt is None:
    return ""
  if isinstance(dt, str):
    return dt
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_entity(row: dict) -> Tag:
  """Convert a DB row to a Tag domain entity."""
  return Tag.reconstitute(
    tid=TagId(row["tid"]),
    username=Username(row["username"]),
    name=TagName(row["name"]),
    created_at=_format_datetime(row.get("created_at")),
    updated_at=_format_datetime(row.get("updated_at")),
  )


class PostgresTagRepository(TagRepository):
  """PostgreSQL implementation of TagRepository for Aurora DSQL."""

  def __init__(self, conn_factory: ConnectionFactory) -> None:
    self._conn_factory = conn_factory

  def _conn(self):
    return self._conn_factory()

  @tracer.capture_method(capture_response=False)
  def find_by_id(self, username: Username, tid: TagId) -> Tag | None:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE tid = %s AND username = %s",
        (tid.value, username.value),
      )
      row = cur.fetchone()
    if not row:
      return None
    return _to_entity(row)

  @tracer.capture_method(capture_response=False)
  def find_all(self, username: Username) -> list[Tag]:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM tags WHERE username = %s ORDER BY name",
        (username.value,),
      )
      rows = cur.fetchall()
    return [_to_entity(row) for row in rows]

  @tracer.capture_method(capture_response=False)
  def count(self, username: Username) -> int:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT COUNT(*) AS cnt FROM tags WHERE username = %s",
        (username.value,),
      )
      row = cur.fetchone()
    return row["cnt"] if row else 0

  @tracer.capture_method(capture_response=False)
  def check_exist(
    self, username: Username, tag_ids: list[TagId]
  ) -> list[TagId]:
    if not tag_ids:
      return []
    conn = self._conn()
    placeholders = ", ".join(["%s"] * len(tag_ids))
    values = [username.value] + [t.value for t in tag_ids]
    with conn.cursor() as cur:
      cur.execute(
        f"SELECT tid FROM tags WHERE username = %s AND tid IN ({placeholders})",
        values,
      )
      return [TagId(row["tid"]) for row in cur.fetchall()]

  @tracer.capture_method(capture_response=False)
  def save(self, tag: Tag) -> Tag:
    conn = self._conn()
    try:
      with conn.transaction():
        with conn.cursor() as cur:
          # Upsert: try update first, then insert
          cur.execute(
            """
            UPDATE tags SET name = %s, updated_at = %s
            WHERE tid = %s AND username = %s
            RETURNING *
            """,
            (tag.name.value, tag.updated_at, tag.tid.value, tag.username.value),
          )
          row = cur.fetchone()
          if row is None:
            cur.execute(
              """
              INSERT INTO tags (tid, username, name, created_at, updated_at)
              VALUES (%s, %s, %s, %s, %s)
              RETURNING *
              """,
              (
                tag.tid.value, tag.username.value, tag.name.value,
                tag.created_at, tag.updated_at,
              ),
            )
            row = cur.fetchone()
    except psycopg.errors.UniqueViolation:
      conn.rollback()
      raise ConflictError(f"Tag name '{tag.name.value}' already exists")

    return _to_entity(row)

  @tracer.capture_method(capture_response=False)
  def delete(self, tag: Tag) -> None:
    conn = self._conn()
    with conn.transaction():
      with conn.cursor() as cur:
        cur.execute(
          "DELETE FROM kifu_tags WHERE tid = %s", (tag.tid.value,)
        )
        cur.execute(
          "DELETE FROM tags WHERE tid = %s AND username = %s",
          (tag.tid.value, tag.username.value),
        )

  @tracer.capture_method(capture_response=False)
  def delete_all_for_user(self, username: Username) -> None:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "DELETE FROM tags WHERE username = %s", (username.value,)
      )

  @tracer.capture_method(capture_response=False)
  def find_kifus_by_tag(
    self, username: Username, tid: TagId
  ) -> list[dict]:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT k.kid, k.slug, k.created_at, k.updated_at
        FROM kifus k
        JOIN kifu_tags kt ON k.kid = kt.kid
        WHERE kt.tid = %s AND k.username = %s
        ORDER BY k.updated_at DESC
        """,
        (tid.value, username.value),
      )
      return [
        {
          "kid": row["kid"],
          "slug": row["slug"],
          "created_at": _format_datetime(row.get("created_at")),
          "updated_at": _format_datetime(row.get("updated_at")),
        }
        for row in cur.fetchall()
      ]
