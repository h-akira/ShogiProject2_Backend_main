from __future__ import annotations

from repositories.db import get_connection


def get_tag(username: str, tid: str) -> dict | None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT * FROM tags WHERE tid = %s AND username = %s",
      (tid, username),
    )
    return cur.fetchone()


def list_tags(username: str) -> list[dict]:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT * FROM tags WHERE username = %s ORDER BY name",
      (username,),
    )
    return cur.fetchall()


def count_tags(username: str) -> int:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      "SELECT COUNT(*) AS cnt FROM tags WHERE username = %s",
      (username,),
    )
    row = cur.fetchone()
    return row["cnt"] if row else 0


def insert_tag(tag: dict) -> dict:
  conn = get_connection()
  columns = list(tag.keys())
  placeholders = ", ".join(["%s"] * len(columns))
  col_names = ", ".join(columns)
  values = [tag[c] for c in columns]
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute(
        f"INSERT INTO tags ({col_names}) VALUES ({placeholders}) RETURNING *",
        values,
      )
      row = cur.fetchone()
  return row


def update_tag(tid: str, username: str, updates: dict) -> dict:
  conn = get_connection()
  set_clauses = ", ".join([f"{k} = %s" for k in updates.keys()])
  values = list(updates.values()) + [tid, username]
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute(
        f"UPDATE tags SET {set_clauses} WHERE tid = %s AND username = %s RETURNING *",
        values,
      )
      row = cur.fetchone()
  return row


def delete_tag(tid: str, username: str) -> None:
  conn = get_connection()
  with conn.transaction():
    with conn.cursor() as cur:
      cur.execute("DELETE FROM kifu_tags WHERE tid = %s", (tid,))
      cur.execute(
        "DELETE FROM tags WHERE tid = %s AND username = %s",
        (tid, username),
      )


def get_kifus_by_tag(username: str, tid: str) -> list[dict]:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT k.kid, k.slug, k.created_at, k.updated_at
      FROM kifus k
      JOIN kifu_tags kt ON k.kid = kt.kid
      WHERE kt.tid = %s AND k.username = %s
      ORDER BY k.updated_at DESC
      """,
      (tid, username),
    )
    return cur.fetchall()


def check_tags_exist(username: str, tag_ids: list[str]) -> list[str]:
  if not tag_ids:
    return []
  conn = get_connection()
  placeholders = ", ".join(["%s"] * len(tag_ids))
  with conn.cursor() as cur:
    cur.execute(
      f"SELECT tid FROM tags WHERE username = %s AND tid IN ({placeholders})",
      [username] + tag_ids,
    )
    return [row["tid"] for row in cur.fetchall()]


def delete_all_tags_for_user(username: str) -> None:
  conn = get_connection()
  with conn.cursor() as cur:
    cur.execute("DELETE FROM tags WHERE username = %s", (username,))
