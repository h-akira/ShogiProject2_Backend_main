"""PostgreSQL implementation of KifuRepository."""

from __future__ import annotations

import psycopg.errors
from aws_lambda_powertools import Tracer

from domain.exceptions import ConflictError
from domain.kifu import Kifu
from domain.repositories import KifuRepository
from domain.value_objects import (
  GameResult,
  KifuId,
  ShareCode,
  Side,
  Slug,
  TagId,
  Username,
)
from infrastructure.db import ConnectionFactory

tracer = Tracer()


def _format_datetime(dt) -> str:
  """Convert DB datetime to ISO 8601 string."""
  if dt is None:
    return ""
  if isinstance(dt, str):
    return dt
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_entity(row: dict, tag_ids: set[TagId] | None = None) -> Kifu:
  """Convert a DB row to a Kifu domain entity."""
  share_code = (
    ShareCode(row["share_code"]) if row.get("share_code") else None
  )
  return Kifu.reconstitute(
    kid=KifuId(row["kid"]),
    username=Username(row["username"]),
    slug=Slug(row["slug"]),
    side=Side(row["side"]),
    result=GameResult(row["result"]),
    memo=row.get("memo", ""),
    kif=row.get("kif", ""),
    shared=row.get("shared", False),
    share_code=share_code,
    tag_ids=tag_ids or set(),
    created_at=_format_datetime(row.get("created_at")),
    updated_at=_format_datetime(row.get("updated_at")),
  )


class PostgresKifuRepository(KifuRepository):
  """PostgreSQL implementation of KifuRepository for Aurora DSQL."""

  def __init__(self, conn_factory: ConnectionFactory) -> None:
    self._conn_factory = conn_factory

  def _conn(self):
    return self._conn_factory()

  @tracer.capture_method(capture_response=False)
  def find_by_id(self, username: Username, kid: KifuId) -> Kifu | None:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE kid = %s AND username = %s",
        (kid.value, username.value),
      )
      row = cur.fetchone()
    if not row:
      return None
    tag_ids = self.get_tag_ids_for_kifu(kid)
    return _to_entity(row, tag_ids)

  @tracer.capture_method(capture_response=False)
  def find_by_id_with_tags(
    self, username: Username, kid: KifuId
  ) -> Kifu | None:
    return self.find_by_id(username, kid)

  @tracer.capture_method(capture_response=False)
  def find_recent(
    self, username: Username, limit: int = 10
  ) -> tuple[list[Kifu], int]:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT k.*, COUNT(*) OVER() AS total_count
        FROM kifus k
        WHERE k.username = %s
        ORDER BY k.updated_at DESC
        LIMIT %s
        """,
        (username.value, limit),
      )
      rows = cur.fetchall()

    if not rows:
      return [], 0

    total_count = rows[0]["total_count"]
    kifus = []
    for row in rows:
      tag_ids = self.get_tag_ids_for_kifu(KifuId(row["kid"]))
      kifus.append(_to_entity(row, tag_ids))
    return kifus, total_count

  @tracer.capture_method(capture_response=False)
  def find_by_slug_prefix(
    self, username: Username, prefix: str
  ) -> list[Kifu]:
    conn = self._conn()
    like_pattern = prefix + "%"
    with conn.cursor() as cur:
      cur.execute(
        "SELECT kid, slug, username, side, result, shared FROM kifus "
        "WHERE username = %s AND slug LIKE %s ORDER BY slug",
        (username.value, like_pattern),
      )
      rows = cur.fetchall()
    # Minimal entity for explorer (no kif/memo needed)
    return [
      _to_entity(
        {**row, "memo": "", "kif": "", "share_code": None,
         "created_at": "", "updated_at": ""},
      )
      for row in rows
    ]

  @tracer.capture_method(capture_response=False)
  def find_by_share_code(self, share_code: ShareCode) -> Kifu | None:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT * FROM kifus WHERE share_code = %s AND shared = TRUE",
        (share_code.value,),
      )
      row = cur.fetchone()
    if not row:
      return None
    return _to_entity(row)

  @tracer.capture_method(capture_response=False)
  def count(self, username: Username) -> int:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT COUNT(*) AS cnt FROM kifus WHERE username = %s",
        (username.value,),
      )
      row = cur.fetchone()
    return row["cnt"] if row else 0

  @tracer.capture_method(capture_response=False)
  def save(self, kifu: Kifu) -> Kifu:
    conn = self._conn()
    try:
      with conn.transaction():
        with conn.cursor() as cur:
          # Upsert: try update first, then insert
          cur.execute(
            """
            UPDATE kifus SET slug = %s, side = %s, result = %s,
              memo = %s, kif = %s, shared = %s, share_code = %s,
              updated_at = %s
            WHERE kid = %s AND username = %s
            RETURNING *
            """,
            (
              kifu.slug.value, kifu.side.value, kifu.result.value,
              kifu.memo, kifu.kif, kifu.shared,
              kifu.share_code.value if kifu.share_code else None,
              kifu.updated_at,
              kifu.kid.value, kifu.username.value,
            ),
          )
          row = cur.fetchone()
          if row is None:
            # New kifu — insert
            cur.execute(
              """
              INSERT INTO kifus (kid, username, slug, side, result,
                memo, kif, shared, share_code, created_at, updated_at)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
              RETURNING *
              """,
              (
                kifu.kid.value, kifu.username.value, kifu.slug.value,
                kifu.side.value, kifu.result.value, kifu.memo, kifu.kif,
                kifu.shared,
                kifu.share_code.value if kifu.share_code else None,
                kifu.created_at, kifu.updated_at,
              ),
            )
            row = cur.fetchone()
    except psycopg.errors.UniqueViolation:
      conn.rollback()
      raise ConflictError(f"slug '{kifu.slug.value}' already exists")

    return _to_entity(row, kifu.tag_ids)

  @tracer.capture_method(capture_response=False)
  def save_tag_associations(
    self, kid: KifuId, to_add: set[TagId], to_remove: set[TagId]
  ) -> None:
    conn = self._conn()
    with conn.transaction():
      with conn.cursor() as cur:
        for tid in to_remove:
          cur.execute(
            "DELETE FROM kifu_tags WHERE kid = %s AND tid = %s",
            (kid.value, tid.value),
          )
        for tid in to_add:
          cur.execute(
            "INSERT INTO kifu_tags (kid, tid) VALUES (%s, %s)",
            (kid.value, tid.value),
          )

  @tracer.capture_method(capture_response=False)
  def delete(self, kifu: Kifu) -> None:
    conn = self._conn()
    with conn.transaction():
      with conn.cursor() as cur:
        cur.execute(
          "DELETE FROM kifu_tags WHERE kid = %s", (kifu.kid.value,)
        )
        cur.execute(
          "DELETE FROM kifus WHERE kid = %s AND username = %s",
          (kifu.kid.value, kifu.username.value),
        )

  @tracer.capture_method(capture_response=False)
  def delete_all_for_user(self, username: Username) -> None:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "DELETE FROM kifu_tags WHERE kid IN "
        "(SELECT kid FROM kifus WHERE username = %s)",
        (username.value,),
      )
      cur.execute(
        "DELETE FROM kifus WHERE username = %s", (username.value,)
      )

  @tracer.capture_method(capture_response=False)
  def get_tag_ids_for_kifu(self, kid: KifuId) -> set[TagId]:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        "SELECT tid FROM kifu_tags WHERE kid = %s", (kid.value,)
      )
      return {TagId(row["tid"]) for row in cur.fetchall()}

  @tracer.capture_method(capture_response=False)
  def get_tag_names_for_kifu(self, kid: KifuId) -> list[dict]:
    conn = self._conn()
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT t.tid, t.name
        FROM tags t
        JOIN kifu_tags kt ON t.tid = kt.tid
        WHERE kt.kid = %s
        ORDER BY t.name
        """,
        (kid.value,),
      )
      return [{"tid": row["tid"], "name": row["name"]} for row in cur.fetchall()]
