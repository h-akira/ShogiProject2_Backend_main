from __future__ import annotations

import psycopg.errors

from common.config import KIFU_MAX
from common.datetime_util import now_iso8601
from common.exceptions import (
  ConflictError,
  LimitExceededError,
  NotFoundError,
  ValidationError,
)
from common.id_generator import generate_id, generate_share_code
from repositories import kifu_repository, tag_repository

VALID_SIDES = {"none", "sente", "gote"}
VALID_RESULTS = {"none", "win", "loss", "sennichite", "jishogi"}


def _normalize_slug(slug: str) -> str:
  if not slug.endswith(".kif"):
    slug = slug + ".kif"
  return slug


def _validate_kifu_input(body: dict) -> None:
  slug = body.get("slug", "")
  if not slug or len(slug) > 255:
    raise ValidationError("slug must be 1-255 characters")
  if slug.startswith("/"):
    raise ValidationError("slug must not start with '/'")

  side = body.get("side", "none")
  if side not in VALID_SIDES:
    raise ValidationError(f"side must be one of: {', '.join(VALID_SIDES)}")

  result = body.get("result", "none")
  if result not in VALID_RESULTS:
    raise ValidationError(f"result must be one of: {', '.join(VALID_RESULTS)}")

  kif = body.get("kif", "")
  if not kif:
    raise ValidationError("kif is required")


def _format_datetime(dt) -> str:
  if dt is None:
    return ""
  if isinstance(dt, str):
    return dt
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_kifu_detail(kifu: dict, tags: list[dict] | None = None) -> dict:
  result = {
    "kid": kifu["kid"],
    "slug": kifu["slug"],
    "side": kifu["side"],
    "result": kifu["result"],
    "tags": tags if tags is not None else kifu.get("tags", []),
    "memo": kifu.get("memo", ""),
    "shared": kifu.get("shared", False),
    "kif": kifu.get("kif", ""),
    "created_at": _format_datetime(kifu.get("created_at")),
    "updated_at": _format_datetime(kifu.get("updated_at")),
  }
  if kifu.get("share_code"):
    result["share_code"] = kifu["share_code"]
  return result


def _build_kifu_summary(kifu: dict) -> dict:
  return {
    "kid": kifu["kid"],
    "slug": kifu["slug"],
    "side": kifu["side"],
    "result": kifu["result"],
    "tags": kifu.get("tags", []),
    "updated_at": _format_datetime(kifu.get("updated_at")),
  }


def create_kifu(username: str, body: dict) -> dict:
  _validate_kifu_input(body)

  count = kifu_repository.count_kifus(username)
  if count >= KIFU_MAX:
    raise LimitExceededError(f"Maximum number of kifus ({KIFU_MAX}) reached")

  tag_ids = body.get("tag_ids", [])
  if tag_ids:
    existing = tag_repository.check_tags_exist(username, tag_ids)
    if len(existing) != len(tag_ids):
      raise ValidationError("Some tag_ids do not exist")

  kid = generate_id()
  now = now_iso8601()
  slug = _normalize_slug(body["slug"])
  shared = body.get("shared", False)

  kifu_data = {
    "kid": kid,
    "username": username,
    "slug": slug,
    "side": body.get("side", "none"),
    "result": body.get("result", "none"),
    "memo": body.get("memo", ""),
    "kif": body["kif"],
    "shared": shared,
    "share_code": generate_share_code() if shared else None,
    "created_at": now,
    "updated_at": now,
  }

  try:
    kifu = kifu_repository.insert_kifu(kifu_data)
  except psycopg.errors.UniqueViolation:
    from repositories.db import get_connection
    get_connection().rollback()
    raise ConflictError(f"slug '{slug}' already exists")

  if tag_ids:
    kifu_repository.insert_kifu_tags(kid, tag_ids)

  tags = [{"tid": t["tid"], "name": t["name"]}
          for t in (tag_repository.get_tag(username, tid) for tid in tag_ids)
          if t is not None] if tag_ids else []

  return _build_kifu_detail(kifu, tags)


def get_kifu(username: str, kid: str) -> dict:
  kifu = kifu_repository.get_kifu_with_tags(username, kid)
  if not kifu:
    raise NotFoundError("Kifu not found")
  return _build_kifu_detail(kifu)


def get_recent_kifus(username: str) -> dict:
  rows = kifu_repository.list_recent_kifus(username)
  total_count = rows[0]["total_count"] if rows else 0
  kifus = [_build_kifu_summary(row) for row in rows]
  return {"kifus": kifus, "total_count": total_count}


def get_explorer(username: str, path: str) -> dict:
  if path and not path.endswith("/"):
    path = path + "/"

  rows = kifu_repository.query_by_slug_prefix(username, path)

  folders: dict[str, int] = {}
  files: list[dict] = []
  depth = len(path.split("/")) - 1 if path else 0

  for row in rows:
    slug = row["slug"]
    parts = slug.split("/")
    if len(parts) == depth + 1:
      # Direct file at this level
      files.append({"kid": row["kid"], "name": parts[-1]})
    elif len(parts) > depth + 1:
      # Folder
      folder_name = parts[depth]
      folders[folder_name] = folders.get(folder_name, 0) + 1

  return {
    "path": path.rstrip("/") if path else "",
    "folders": [{"name": name, "count": count} for name, count in sorted(folders.items())],
    "files": files,
  }


def update_kifu(username: str, kid: str, body: dict) -> dict:
  existing = kifu_repository.get_kifu(username, kid)
  if not existing:
    raise NotFoundError("Kifu not found")

  _validate_kifu_input(body)

  tag_ids = body.get("tag_ids")
  if tag_ids is not None:
    existing_tags = tag_repository.check_tags_exist(username, tag_ids)
    if len(existing_tags) != len(tag_ids):
      raise ValidationError("Some tag_ids do not exist")

  slug = _normalize_slug(body["slug"])
  shared = body.get("shared", existing["shared"])
  now = now_iso8601()

  # Handle share_code logic
  share_code = existing.get("share_code")
  if shared and not share_code:
    share_code = generate_share_code()
  elif not shared:
    share_code = None

  updates = {
    "slug": slug,
    "side": body.get("side", "none"),
    "result": body.get("result", "none"),
    "memo": body.get("memo", ""),
    "kif": body["kif"],
    "shared": shared,
    "share_code": share_code,
    "updated_at": now,
  }

  try:
    kifu = kifu_repository.update_kifu(kid, username, updates)
  except psycopg.errors.UniqueViolation:
    from repositories.db import get_connection
    get_connection().rollback()
    raise ConflictError(f"slug '{slug}' already exists")

  # Sync tag associations
  if tag_ids is not None:
    current_tag_ids = set(kifu_repository.get_tag_ids_for_kifu(kid))
    new_tag_ids = set(tag_ids)
    to_add = list(new_tag_ids - current_tag_ids)
    to_remove = list(current_tag_ids - new_tag_ids)
    if to_remove:
      kifu_repository.delete_kifu_tags(kid, to_remove)
    if to_add:
      kifu_repository.insert_kifu_tags(kid, to_add)

  return get_kifu(username, kid)


def delete_kifu(username: str, kid: str) -> None:
  existing = kifu_repository.get_kifu(username, kid)
  if not existing:
    raise NotFoundError("Kifu not found")
  kifu_repository.delete_kifu(kid, username)


def get_shared_kifu(share_code: str) -> dict:
  kifu = kifu_repository.get_shared_kifu(share_code)
  if not kifu:
    raise NotFoundError("Shared kifu not found")
  return {
    "slug": kifu["slug"],
    "side": kifu["side"],
    "result": kifu["result"],
    "memo": kifu.get("memo", ""),
    "kif": kifu.get("kif", ""),
    "created_at": _format_datetime(kifu.get("created_at")),
    "updated_at": _format_datetime(kifu.get("updated_at")),
  }


def regenerate_share_code(username: str, kid: str) -> dict:
  existing = kifu_repository.get_kifu(username, kid)
  if not existing:
    raise NotFoundError("Kifu not found")

  new_share_code = generate_share_code()
  now = now_iso8601()
  kifu_repository.update_kifu(kid, username, {
    "share_code": new_share_code,
    "updated_at": now,
  })

  return {"share_code": new_share_code}
