from __future__ import annotations

from repositories.db import get_connection


def get_kifu(username: str, kid: str) -> dict | None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT * FROM kifus WHERE kid = %s AND username = %s",
      (kid, username),
    )
    return cur.fetchone()


def get_kifu_with_tags(username: str, kid: str) -> dict | None:
  conn = get_connection()
  with conn.cursor() as cur:
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
      (kid, username),
    )
    return cur.fetchone()


def list_recent_kifus(username: str, limit: int = 10) -> list[dict]:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT k.kid, k.slug, k.side, k.result, k.updated_at,
             COUNT(*) OVER() AS total_count,
             COALESCE(
               json_agg(json_build_object('tid', t.tid, 'name', t.name))
               FILTER (WHERE t.tid IS NOT NULL),
               '[]'::json
             ) AS tags
      FROM kifus k
      LEFT JOIN kifu_tags kt ON k.kid = kt.kid
      LEFT JOIN tags t ON kt.tid = t.tid
      WHERE k.username = %s
      GROUP BY k.kid
      ORDER BY k.updated_at DESC
      LIMIT %s
      """,
      (username, limit),
    )
    return cur.fetchall()


def count_kifus(username: str) -> int:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT COUNT(*) AS cnt FROM kifus WHERE username = %s",
      (username,),
    )
    row = cur.fetchone()
    return row["cnt"] if row else 0


def insert_kifu(kifu: dict) -> dict:
  conn = get_connection()
  columns = list(kifu.keys())
  placeholders = ", ".join(["%s"] * len(columns))
  col_names = ", ".join(columns)
  values = [kifu[c] for c in columns]
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute(
        f"INSERT INTO kifus ({col_names}) VALUES ({placeholders}) RETURNING *",
        values,
      )
      row = cur.fetchone()
  return row


def update_kifu(kid: str, username: str, updates: dict) -> dict:
  conn = get_connection()
  set_clauses = ", ".join([f"{k} = %s" for k in updates.keys()])
  values = list(updates.values()) + [kid, username]
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute(
        f"UPDATE kifus SET {set_clauses} WHERE kid = %s AND username = %s RETURNING *",
        values,
      )
      row = cur.fetchone()
  return row


def delete_kifu(kid: str, username: str) -> None:
  conn = get_connection()
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute("DELETE FROM kifu_tags WHERE kid = %s", (kid,))
      cur.execute(
        "DELETE FROM kifus WHERE kid = %s AND username = %s",
        (kid, username),
      )


def query_by_slug_prefix(username: str, prefix: str) -> list[dict]:
  conn = get_connection()
  like_pattern = prefix + "%"
  with conn.cursor() as cur:
    cur.execute(
      "SELECT kid, slug FROM kifus WHERE username = %s AND slug LIKE %s ORDER BY slug",
      (username, like_pattern),
    )
    return cur.fetchall()


def get_shared_kifu(share_code: str) -> dict | None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT * FROM kifus WHERE share_code = %s AND shared = TRUE",
      (share_code,),
    )
    return cur.fetchone()


def get_tag_ids_for_kifu(kid: str) -> list[str]:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute("SELECT tid FROM kifu_tags WHERE kid = %s", (kid,))
    return [row["tid"] for row in cur.fetchall()]


def insert_kifu_tags(kid: str, tag_ids: list[str]) -> None:
  if not tag_ids:
    return
  conn = get_connection()
  with conn.transaction():
    with conn.cursor() as cur:
      for tid in tag_ids:
        cur.execute(
          "INSERT INTO kifu_tags (kid, tid) VALUES (%s, %s)",
          (kid, tid),
        )


def delete_kifu_tags(kid: str, tag_ids: list[str]) -> None:
  if not tag_ids:
    return
  conn = get_connection()
  with conn.transaction():
    with conn.cursor() as cur:
      for tid in tag_ids:
        cur.execute(
          "DELETE FROM kifu_tags WHERE kid = %s AND tid = %s",
          (kid, tid),
        )


def delete_all_kifu_tags_for_user(username: str) -> None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "DELETE FROM kifu_tags WHERE kid IN (SELECT kid FROM kifus WHERE username = %s)",
      (username,),
    )


def delete_all_kifus_for_user(username: str) -> None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute("DELETE FROM kifus WHERE username = %s", (username,))
