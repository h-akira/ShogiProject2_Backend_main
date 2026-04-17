"""Tests for Tag use cases using InMemoryRepository."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from application.dto import (
  CreateTagCommand,
  DeleteTagCommand,
  GetTagCommand,
  GetTagsCommand,
  UpdateTagCommand,
)
from application.tag_use_cases import (
  CreateTagUseCase,
  DeleteTagUseCase,
  GetTagsUseCase,
  GetTagUseCase,
  UpdateTagUseCase,
)
from domain.exceptions import (
  ConflictError,
  EntityNotFoundError,
  LimitExceededError,
)

from .helpers.in_memory_repositories import InMemoryTagRepository

MOCK_ID = "tag111111111"


@pytest.fixture
def tag_repo():
  return InMemoryTagRepository()


class TestCreateTagUseCase:
  @patch("application.tag_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, tag_repo):
    uc = CreateTagUseCase(tag_repo, tag_max=50)
    result = uc.execute(CreateTagCommand(
      username="testuser", name="opening",
    ))
    assert result.tid == MOCK_ID
    assert result.name == "opening"
    assert result.created_at == "2024-01-01T00:00:00Z"

  @patch("application.tag_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_limit_exceeded(self, _now, _gen_id, tag_repo):
    uc = CreateTagUseCase(tag_repo, tag_max=0)
    with pytest.raises(LimitExceededError, match="Maximum"):
      uc.execute(CreateTagCommand(username="testuser", name="opening"))

  @patch("application.tag_use_cases.generate_id")
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_name_conflict(self, _now, mock_gen_id, tag_repo):
    uc = CreateTagUseCase(tag_repo, tag_max=50)

    mock_gen_id.return_value = "tag111111111"
    uc.execute(CreateTagCommand(username="testuser", name="opening"))

    mock_gen_id.return_value = "tag222222222"
    with pytest.raises(ConflictError, match="already exists"):
      uc.execute(CreateTagCommand(username="testuser", name="opening"))


class TestGetTagsUseCase:
  @patch("application.tag_use_cases.generate_id")
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, mock_gen_id, tag_repo):
    create_uc = CreateTagUseCase(tag_repo, tag_max=50)

    mock_gen_id.return_value = "tag111111111"
    create_uc.execute(CreateTagCommand(username="testuser", name="opening"))
    mock_gen_id.return_value = "tag222222222"
    create_uc.execute(CreateTagCommand(username="testuser", name="endgame"))

    uc = GetTagsUseCase(tag_repo)
    result = uc.execute(GetTagsCommand(username="testuser"))
    assert len(result) == 2
    # Sorted by name
    assert result[0].name == "endgame"
    assert result[1].name == "opening"

  def test_empty(self, tag_repo):
    uc = GetTagsUseCase(tag_repo)
    result = uc.execute(GetTagsCommand(username="testuser"))
    assert result == []


class TestGetTagUseCase:
  @patch("application.tag_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, tag_repo):
    create_uc = CreateTagUseCase(tag_repo, tag_max=50)
    create_uc.execute(CreateTagCommand(username="testuser", name="opening"))

    tag_repo.set_kifu_association(MOCK_ID, [
      {"kid": "kid000000001", "slug": "game.kif",
       "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
    ])

    uc = GetTagUseCase(tag_repo)
    result = uc.execute(GetTagCommand(username="testuser", tid=MOCK_ID))
    assert result.name == "opening"
    assert len(result.kifus) == 1

  def test_not_found(self, tag_repo):
    uc = GetTagUseCase(tag_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(GetTagCommand(username="testuser", tid=MOCK_ID))


class TestUpdateTagUseCase:
  @patch("application.tag_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, tag_repo):
    create_uc = CreateTagUseCase(tag_repo, tag_max=50)
    create_uc.execute(CreateTagCommand(username="testuser", name="opening"))

    with patch("application.tag_use_cases.now_iso8601", return_value="2024-06-01T00:00:00Z"):
      uc = UpdateTagUseCase(tag_repo)
      result = uc.execute(UpdateTagCommand(
        username="testuser", tid=MOCK_ID, name="endgame",
      ))
    assert result.name == "endgame"
    assert result.updated_at == "2024-06-01T00:00:00Z"

  def test_not_found(self, tag_repo):
    uc = UpdateTagUseCase(tag_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(UpdateTagCommand(
        username="testuser", tid=MOCK_ID, name="new_name",
      ))


class TestDeleteTagUseCase:
  @patch("application.tag_use_cases.generate_id", return_value=MOCK_ID)
  @patch("application.tag_use_cases.now_iso8601", return_value="2024-01-01T00:00:00Z")
  def test_success(self, _now, _gen_id, tag_repo):
    create_uc = CreateTagUseCase(tag_repo, tag_max=50)
    create_uc.execute(CreateTagCommand(username="testuser", name="opening"))

    uc = DeleteTagUseCase(tag_repo)
    uc.execute(DeleteTagCommand(username="testuser", tid=MOCK_ID))

    get_uc = GetTagUseCase(tag_repo)
    with pytest.raises(EntityNotFoundError):
      get_uc.execute(GetTagCommand(username="testuser", tid=MOCK_ID))

  def test_not_found(self, tag_repo):
    uc = DeleteTagUseCase(tag_repo)
    with pytest.raises(EntityNotFoundError):
      uc.execute(DeleteTagCommand(username="testuser", tid=MOCK_ID))
