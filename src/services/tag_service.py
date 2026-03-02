from __future__ import annotations

import psycopg.errors

from common.config import TAG_MAX
from common.datetime_util import now_iso8601
from common.exceptions import (
  ConflictError,
  LimitExceededError,
  NotFoundError,
  ValidationError,
)
from common.id_generator import generate_id
from repositories import tag_repository


def _validate_tag_name(name: str) -> None:
  if not name or len(name) > 127:
    raise ValidationError("Tag name must be 1-127 characters")


def _format_datetime(dt) -> str:
  if dt is None:
    return ""
  if isinstance(dt, str):
    return dt
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_tag(tag: dict) -> dict:
  return {
    "tid": tag["tid"],
    "name": tag["name"],
    "created_at": _format_datetime(tag.get("created_at")),
    "updated_at": _format_datetime(tag.get("updated_at")),
  }


def create_tag(username: str, body: dict) -> dict:
  name = body.get("name", "")
  _validate_tag_name(name)

  count = tag_repository.count_tags(username)
  if count >= TAG_MAX:
    raise LimitExceededError(f"Maximum number of tags ({TAG_MAX}) reached")

  tid = generate_id()
  now = now_iso8601()

  tag_data = {
    "tid": tid,
    "username": username,
    "name": name,
    "created_at": now,
    "updated_at": now,
  }

  try:
    tag = tag_repository.insert_tag(tag_data)
  except psycopg.errors.UniqueViolation:
    from repositories.db import get_connection
    get_connection().rollback()
    raise ConflictError(f"Tag name '{name}' already exists")

  return _build_tag(tag)


def get_tags(username: str) -> list[dict]:
  tags = tag_repository.list_tags(username)
  return [_build_tag(t) for t in tags]


def get_tag(username: str, tid: str) -> dict:
  tag = tag_repository.get_tag(username, tid)
  if not tag:
    raise NotFoundError("Tag not found")

  kifus = tag_repository.get_kifus_by_tag(username, tid)
  kifu_summaries = [
    {
      "kid": k["kid"],
      "slug": k["slug"],
      "created_at": _format_datetime(k.get("created_at")),
      "updated_at": _format_datetime(k.get("updated_at")),
    }
    for k in kifus
  ]

  result = _build_tag(tag)
  result["kifus"] = kifu_summaries
  return result


def update_tag(username: str, tid: str, body: dict) -> dict:
  existing = tag_repository.get_tag(username, tid)
  if not existing:
    raise NotFoundError("Tag not found")

  name = body.get("name", "")
  _validate_tag_name(name)

  now = now_iso8601()
  updates = {"name": name, "updated_at": now}

  try:
    tag = tag_repository.update_tag(tid, username, updates)
  except psycopg.errors.UniqueViolation:
    from repositories.db import get_connection
    get_connection().rollback()
    raise ConflictError(f"Tag name '{name}' already exists")

  return _build_tag(tag)


def delete_tag(username: str, tid: str) -> None:
  existing = tag_repository.get_tag(username, tid)
  if not existing:
    raise NotFoundError("Tag not found")
  tag_repository.delete_tag(tid, username)
