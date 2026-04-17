"""Tag-related use cases."""

from __future__ import annotations

from common.datetime_util import now_iso8601
from common.id_generator import generate_id

from domain.exceptions import EntityNotFoundError, LimitExceededError
from domain.repositories import TagRepository
from domain.tag import Tag
from domain.value_objects import TagId, TagName, Username

from application.dto import (
  CreateTagCommand,
  DeleteTagCommand,
  GetTagCommand,
  GetTagsCommand,
  TagDetailResponse,
  TagResponse,
  UpdateTagCommand,
)


def _build_tag_response(tag: Tag) -> TagResponse:
  return TagResponse(
    tid=tag.tid.value,
    name=tag.name.value,
    created_at=tag.created_at,
    updated_at=tag.updated_at,
  )


class CreateTagUseCase:
  def __init__(self, tag_repo: TagRepository, tag_max: int) -> None:
    self._tag_repo = tag_repo
    self._tag_max = tag_max

  def execute(self, command: CreateTagCommand) -> TagResponse:
    username = Username(command.username)
    name = TagName(command.name)

    count = self._tag_repo.count(username)
    if count >= self._tag_max:
      raise LimitExceededError(
        f"Maximum number of tags ({self._tag_max}) reached"
      )

    tid = TagId(generate_id())
    now = now_iso8601()
    tag = Tag.create(tid=tid, username=username, name=name, now=now)
    tag = self._tag_repo.save(tag)

    return _build_tag_response(tag)


class GetTagsUseCase:
  def __init__(self, tag_repo: TagRepository) -> None:
    self._tag_repo = tag_repo

  def execute(self, command: GetTagsCommand) -> list[TagResponse]:
    username = Username(command.username)
    tags = self._tag_repo.find_all(username)
    return [_build_tag_response(t) for t in tags]


class GetTagUseCase:
  def __init__(self, tag_repo: TagRepository) -> None:
    self._tag_repo = tag_repo

  def execute(self, command: GetTagCommand) -> TagDetailResponse:
    username = Username(command.username)
    tid = TagId(command.tid)

    tag = self._tag_repo.find_by_id(username, tid)
    if not tag:
      raise EntityNotFoundError("Tag not found")

    kifus = self._tag_repo.find_kifus_by_tag(username, tid)

    return TagDetailResponse(
      tid=tag.tid.value,
      name=tag.name.value,
      created_at=tag.created_at,
      updated_at=tag.updated_at,
      kifus=kifus,
    )


class UpdateTagUseCase:
  def __init__(self, tag_repo: TagRepository) -> None:
    self._tag_repo = tag_repo

  def execute(self, command: UpdateTagCommand) -> TagResponse:
    username = Username(command.username)
    tid = TagId(command.tid)

    tag = self._tag_repo.find_by_id(username, tid)
    if not tag:
      raise EntityNotFoundError("Tag not found")

    new_name = TagName(command.name)
    now = now_iso8601()
    tag.rename(new_name, now)
    tag = self._tag_repo.save(tag)

    return _build_tag_response(tag)


class DeleteTagUseCase:
  def __init__(self, tag_repo: TagRepository) -> None:
    self._tag_repo = tag_repo

  def execute(self, command: DeleteTagCommand) -> None:
    username = Username(command.username)
    tid = TagId(command.tid)

    tag = self._tag_repo.find_by_id(username, tid)
    if not tag:
      raise EntityNotFoundError("Tag not found")

    self._tag_repo.delete(tag)
