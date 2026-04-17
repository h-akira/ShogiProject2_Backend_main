"""Tests for Kifu use cases using InMemoryRepository."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from application.dto import (
  CreateKifuCommand,
  DeleteKifuCommand,
  GetExplorerCommand,
  GetKifuCommand,
  GetRecentKifusCommand,
  GetSharedKifuCommand,
  RegenerateShareCodeCommand,
  UpdateKifuCommand,
)
from application.kifu_use_cases import (
  CreateKifuUseCase,
  DeleteKifuUseCase,
  GetExplorerUseCase,
  GetKifuUseCase,
  GetRecentKifusUseCase,
  GetSharedKifuUseCase,
  RegenerateShareCodeUseCase,
  UpdateKifuUseCase,
)
from domain.exceptions import (
  ConflictError,
  DomainValidationError,
  EntityNotFoundError,
  LimitExceededError,
)
from domain.tag import Tag
from domain.value_objects import TagId, TagName, Username

from .helpers.in_memory_repositories import (
  InMemoryKifuRepository,
  InMemoryTagRepository,
)

MOCK_ID = "abcdef123456"
MOCK_SHARE_CODE = "a" * 36


@pytest.fixture
def kifu_repo():
  return InMemoryKifuRepository()


@pytest.fixture
def tag_repo():
  return InMemoryTagRepository()


def _create_tag_in_repo(tag_repo: InMemoryTagRepository, tid: str, name: str) -> None:
  tag = Tag.create(
    tid=TagId(tid),
    username=Username("testuser"),
    name=TagName(name),
    now="2024-01-01T00:00:00Z",
  )
  tag_repo.save(tag)


class TestCreateKifuUseCase:
  @patch("application.kifu_use_cases.generate_share_code", return_value=MOCK_SHARE_CODE)
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, _gen_sc, kifu_repo, tag_repo):
    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    result = uc.execute(CreateKifuCommand(
      username="testuser",
      slug="year/2024/game",
      side="sente",
      result="win",
      memo="test",
      kif="kif data",
      shared=False,
      tag_ids=[],
    ))
    assert result.kid == MOCK_ID
    assert result.slug == "year/2024/game.kif"
    assert result.side == "sente"
    assert result.result == "win"
    assert result.shared is False
    assert result.share_code is None

  @patch("application.kifu_use_cases.generate_share_code", return_value=MOCK_SHARE_CODE)
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_with_sharing(self, _now, _gen_id, _gen_sc, kifu_repo, tag_repo):
    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    result = uc.execute(CreateKifuCommand(
      username="testuser",
      slug="game",
      side="none",
      result="none",
      memo="",
      kif="data",
      shared=True,
      tag_ids=[],
    ))
    assert result.shared is True
    assert result.share_code == MOCK_SHARE_CODE

  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_with_tags(self, _now, _gen_id, kifu_repo, tag_repo):
    _create_tag_in_repo(tag_repo, "tag111111111", "opening")
    kifu_repo.set_tag_name("tag111111111", "opening")

    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    result = uc.execute(CreateKifuCommand(
      username="testuser",
      slug="game",
      side="none",
      result="none",
      memo="",
      kif="data",
      shared=False,
      tag_ids=["tag111111111"],
    ))
    assert len(result.tags) == 1
    assert result.tags[0]["name"] == "opening"

  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_limit_exceeded(self, _now, _gen_id, kifu_repo, tag_repo):
    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=0)
    with pytest.raises(LimitExceededError, match="Maximum"):
      uc.execute(CreateKifuCommand(
        username="testuser",
        slug="game",
        side="none",
        result="none",
        memo="",
        kif="data",
        shared=False,
      ))

  def test_invalid_side(self, kifu_repo, tag_repo):
    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    with pytest.raises(ValueError):
      uc.execute(CreateKifuCommand(
        username="testuser",
        slug="game",
        side="invalid",
        result="none",
        memo="",
        kif="data",
        shared=False,
      ))

  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_tag_not_found(self, _now, _gen_id, kifu_repo, tag_repo):
    uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    with pytest.raises(DomainValidationError, match="tag_ids"):
      uc.execute(CreateKifuCommand(
        username="testuser",
        slug="game",
        side="none",
        result="none",
        memo="",
        kif="data",
        shared=False,
        tag_ids=["nonexiste000"],
      ))


class TestGetKifuUseCase:
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, kifu_repo, tag_repo):
    # Create a kifu first
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="none",
      result="none", memo="", kif="data", shared=False,
    ))

    uc = GetKifuUseCase(kifu_repo)
    result = uc.execute(GetKifuCommand(username="testuser", kid=MOCK_ID))
    assert result.kid == MOCK_ID

  def test_not_found(self, kifu_repo):
    uc = GetKifuUseCase(kifu_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(GetKifuCommand(username="testuser", kid=MOCK_ID))


class TestGetRecentKifusUseCase:
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="none",
      result="none", memo="", kif="data", shared=False,
    ))

    uc = GetRecentKifusUseCase(kifu_repo)
    result = uc.execute(GetRecentKifusCommand(username="testuser"))
    assert result.total_count == 1
    assert len(result.kifus) == 1

  def test_empty(self, kifu_repo):
    uc = GetRecentKifusUseCase(kifu_repo)
    result = uc.execute(GetRecentKifusCommand(username="testuser"))
    assert result.total_count == 0
    assert result.kifus == []


class TestGetExplorerUseCase:
  @patch("application.kifu_use_cases.generate_id")
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, mock_gen_id, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)

    mock_gen_id.return_value = "kid000000001"
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="year/2024/game1", side="none",
      result="none", memo="", kif="data", shared=False,
    ))
    mock_gen_id.return_value = "kid000000002"
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="year/2024/game2", side="none",
      result="none", memo="", kif="data", shared=False,
    ))

    uc = GetExplorerUseCase(kifu_repo)
    result = uc.execute(GetExplorerCommand(
      username="testuser", path="year/2024",
    ))
    assert result.path == "year/2024"
    assert len(result.files) == 2


class TestUpdateKifuUseCase:
  @patch("application.kifu_use_cases.generate_share_code", return_value=MOCK_SHARE_CODE)
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, _gen_sc, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="none",
      result="none", memo="", kif="data", shared=False,
    ))

    uc = UpdateKifuUseCase(kifu_repo, tag_repo)
    result = uc.execute(UpdateKifuCommand(
      username="testuser", kid=MOCK_ID,
      slug="new_game", side="sente", result="win",
      memo="updated", kif="new data", shared=False,
    ))
    assert result.slug == "new_game.kif"
    assert result.side == "sente"
    assert result.memo == "updated"

  def test_not_found(self, kifu_repo, tag_repo):
    uc = UpdateKifuUseCase(kifu_repo, tag_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(UpdateKifuCommand(
        username="testuser", kid=MOCK_ID,
        slug="game", side="none", result="none",
        memo="", kif="data", shared=False,
      ))


class TestDeleteKifuUseCase:
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="none",
      result="none", memo="", kif="data", shared=False,
    ))

    uc = DeleteKifuUseCase(kifu_repo)
    uc.execute(DeleteKifuCommand(username="testuser", kid=MOCK_ID))

    # Verify deleted
    get_uc = GetKifuUseCase(kifu_repo)
    with pytest.raises(EntityNotFoundError):
      get_uc.execute(GetKifuCommand(username="testuser", kid=MOCK_ID))

  def test_not_found(self, kifu_repo):
    uc = DeleteKifuUseCase(kifu_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(DeleteKifuCommand(username="testuser", kid=MOCK_ID))


class TestGetSharedKifuUseCase:
  @patch("application.kifu_use_cases.generate_share_code", return_value=MOCK_SHARE_CODE)
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, _gen_sc, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="sente",
      result="win", memo="memo", kif="data", shared=True,
    ))

    uc = GetSharedKifuUseCase(kifu_repo)
    result = uc.execute(GetSharedKifuCommand(share_code=MOCK_SHARE_CODE))
    assert result.slug == "game.kif"
    assert result.side == "sente"
    assert result.result == "win"

  def test_not_found(self, kifu_repo):
    uc = GetSharedKifuUseCase(kifu_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(GetSharedKifuCommand(share_code=MOCK_SHARE_CODE))


class TestRegenerateShareCodeUseCase:
  @patch("application.kifu_use_cases.generate_share_code", return_value=MOCK_SHARE_CODE)
  @patch("application.kifu_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.kifu_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, _gen_sc, kifu_repo, tag_repo):
    create_uc = CreateKifuUseCase(kifu_repo, tag_repo, kifu_max=2000)
    create_uc.execute(CreateKifuCommand(
      username="testuser", slug="game", side="none",
      result="none", memo="", kif="data", shared=True,
    ))

    new_code = "b" * 36
    with patch("application.kifu_use_cases.generate_share_code", return_value=new_code):
      with patch("application.kifu_use_cases.now_iso8601", return_value="2024-06-01T00:00:00Z"):
        uc = RegenerateShareCodeUseCase(kifu_repo)
        result = uc.execute(RegenerateShareCodeCommand(
          username="testuser", kid=MOCK_ID,
        ))
    assert result.share_code == new_code

  def test_not_found(self, kifu_repo):
    uc = RegenerateShareCodeUseCase(kifu_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(RegenerateShareCodeCommand(
        username="testuser", kid=MOCK_ID,
      ))
