"""Kifu-related use cases."""

from __future__ import annotations

from common.datetime_util import now_iso8601
from common.id_generator import generate_id, generate_share_code

from domain.exceptions import (
  DomainValidationError,
  EntityNotFoundError,
  LimitExceededError,
)
from domain.kifu import Kifu
from domain.repositories import KifuRepository, TagRepository
from domain.services import KifuExplorerService
from domain.value_objects import (
  GameResult,
  KifuId,
  ShareCode,
  Side,
  Slug,
  TagId,
  Username,
)

from application.dto import (
  CreateKifuCommand,
  DeleteKifuCommand,
  ExplorerResponse,
  GetExplorerCommand,
  GetKifuCommand,
  GetRecentKifusCommand,
  GetSharedKifuCommand,
  KifuDetailResponse,
  KifuSummaryResponse,
  RecentKifusResponse,
  RegenerateShareCodeCommand,
  ShareCodeResponse,
  SharedKifuResponse,
  UpdateKifuCommand,
)


def _build_kifu_detail(kifu: Kifu, tags: list[dict]) -> KifuDetailResponse:
  return KifuDetailResponse(
    kid=kifu.kid.value,
    slug=kifu.slug.value,
    side=kifu.side.value,
    result=kifu.result.value,
    tags=tags,
    memo=kifu.memo,
    shared=kifu.shared,
    kif=kifu.kif,
    share_code=kifu.share_code.value if kifu.share_code else None,
    created_at=kifu.created_at,
    updated_at=kifu.updated_at,
  )


def _build_kifu_summary(kifu: Kifu, tags: list[dict]) -> KifuSummaryResponse:
  return KifuSummaryResponse(
    kid=kifu.kid.value,
    slug=kifu.slug.value,
    side=kifu.side.value,
    result=kifu.result.value,
    tags=tags,
    updated_at=kifu.updated_at,
  )


class CreateKifuUseCase:
  def __init__(
    self, kifu_repo: KifuRepository, tag_repo: TagRepository, kifu_max: int
  ) -> None:
    self._kifu_repo = kifu_repo
    self._tag_repo = tag_repo
    self._kifu_max = kifu_max

  def execute(self, command: CreateKifuCommand) -> KifuDetailResponse:
    username = Username(command.username)

    # Check limit
    count = self._kifu_repo.count(username)
    if count >= self._kifu_max:
      raise LimitExceededError(
        f"Maximum number of kifus ({self._kifu_max}) reached"
      )

    # Validate tags exist
    tag_id_vos = [TagId(tid) for tid in command.tag_ids]
    if tag_id_vos:
      existing = self._tag_repo.check_exist(username, tag_id_vos)
      if len(existing) != len(tag_id_vos):
        raise DomainValidationError("Some tag_ids do not exist")

    # Build value objects (validation happens here)
    slug = Slug(command.slug)
    side = Side(command.side)
    result = GameResult(command.result)
    kid = KifuId(generate_id())
    shared = command.shared
    share_code = ShareCode(generate_share_code()) if shared else None

    # Create entity
    now = now_iso8601()
    kifu = Kifu.create(
      kid=kid,
      username=username,
      slug=slug,
      side=side,
      result=result,
      memo=command.memo,
      kif=command.kif,
      shared=shared,
      share_code=share_code,
      tag_ids=set(tag_id_vos),
      now=now,
    )

    # Persist
    kifu = self._kifu_repo.save(kifu)
    if tag_id_vos:
      self._kifu_repo.save_tag_associations(kid, set(tag_id_vos), set())

    # Build tag names for response
    tags = self._kifu_repo.get_tag_names_for_kifu(kid) if tag_id_vos else []

    return _build_kifu_detail(kifu, tags)


class GetKifuUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(self, command: GetKifuCommand) -> KifuDetailResponse:
    username = Username(command.username)
    kid = KifuId(command.kid)

    kifu = self._kifu_repo.find_by_id_with_tags(username, kid)
    if not kifu:
      raise EntityNotFoundError("Kifu not found")

    tags = self._kifu_repo.get_tag_names_for_kifu(kid)
    return _build_kifu_detail(kifu, tags)


class GetRecentKifusUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(self, command: GetRecentKifusCommand) -> RecentKifusResponse:
    username = Username(command.username)
    kifus, total_count = self._kifu_repo.find_recent(username)

    summaries = []
    for kifu in kifus:
      tags = self._kifu_repo.get_tag_names_for_kifu(kifu.kid)
      summaries.append(_build_kifu_summary(kifu, tags))

    return RecentKifusResponse(kifus=summaries, total_count=total_count)


class GetExplorerUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(self, command: GetExplorerCommand) -> ExplorerResponse:
    username = Username(command.username)
    kifus = self._kifu_repo.find_by_slug_prefix(username, command.path)
    result = KifuExplorerService.classify(kifus, command.path)
    return ExplorerResponse(
      path=result.path,
      folders=[{"name": f.name, "count": f.count} for f in result.folders],
      files=[{"kid": f.kid, "name": f.name} for f in result.files],
    )


class UpdateKifuUseCase:
  def __init__(
    self, kifu_repo: KifuRepository, tag_repo: TagRepository
  ) -> None:
    self._kifu_repo = kifu_repo
    self._tag_repo = tag_repo

  def execute(self, command: UpdateKifuCommand) -> KifuDetailResponse:
    username = Username(command.username)
    kid = KifuId(command.kid)

    kifu = self._kifu_repo.find_by_id(username, kid)
    if not kifu:
      raise EntityNotFoundError("Kifu not found")

    # Validate tags if provided
    tag_id_vos: list[TagId] | None = None
    if command.tag_ids is not None:
      tag_id_vos = [TagId(tid) for tid in command.tag_ids]
      existing = self._tag_repo.check_exist(username, tag_id_vos)
      if len(existing) != len(tag_id_vos):
        raise DomainValidationError("Some tag_ids do not exist")

    # Build value objects
    slug = Slug(command.slug)
    side = Side(command.side)
    result = GameResult(command.result)
    shared = command.shared
    now = now_iso8601()

    # Handle share_code logic
    share_code = kifu.share_code
    if shared and not share_code:
      share_code = ShareCode(generate_share_code())
    elif not shared:
      share_code = None

    # Update entity
    kifu.update(
      slug=slug,
      side=side,
      result=result,
      memo=command.memo,
      kif=command.kif,
      shared=shared,
      share_code=share_code,
      now=now,
    )

    # Persist
    kifu = self._kifu_repo.save(kifu)

    # Sync tag associations
    if tag_id_vos is not None:
      current_tag_ids = self._kifu_repo.get_tag_ids_for_kifu(kid)
      new_tag_ids = set(tag_id_vos)
      to_add = new_tag_ids - current_tag_ids
      to_remove = current_tag_ids - new_tag_ids
      if to_add or to_remove:
        self._kifu_repo.save_tag_associations(kid, to_add, to_remove)
      kifu.apply_tag_changes(new_tag_ids)

    # Re-fetch with tags for response
    tags = self._kifu_repo.get_tag_names_for_kifu(kid)
    return _build_kifu_detail(kifu, tags)


class DeleteKifuUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(self, command: DeleteKifuCommand) -> None:
    username = Username(command.username)
    kid = KifuId(command.kid)

    kifu = self._kifu_repo.find_by_id(username, kid)
    if not kifu:
      raise EntityNotFoundError("Kifu not found")

    self._kifu_repo.delete(kifu)


class GetSharedKifuUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(self, command: GetSharedKifuCommand) -> SharedKifuResponse:
    share_code = ShareCode(command.share_code)
    kifu = self._kifu_repo.find_by_share_code(share_code)
    if not kifu:
      raise EntityNotFoundError("Shared kifu not found")

    return SharedKifuResponse(
      slug=kifu.slug.value,
      side=kifu.side.value,
      result=kifu.result.value,
      memo=kifu.memo,
      kif=kifu.kif,
      created_at=kifu.created_at,
      updated_at=kifu.updated_at,
    )


class RegenerateShareCodeUseCase:
  def __init__(self, kifu_repo: KifuRepository) -> None:
    self._kifu_repo = kifu_repo

  def execute(
    self, command: RegenerateShareCodeCommand
  ) -> ShareCodeResponse:
    username = Username(command.username)
    kid = KifuId(command.kid)

    kifu = self._kifu_repo.find_by_id(username, kid)
    if not kifu:
      raise EntityNotFoundError("Kifu not found")

    new_code = ShareCode(generate_share_code())
    now = now_iso8601()
    kifu.regenerate_share_code(new_code, now)
    self._kifu_repo.save(kifu)

    return ShareCodeResponse(share_code=new_code.value)
