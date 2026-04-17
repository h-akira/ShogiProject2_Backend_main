"""Tests for User use cases."""

from __future__ import annotations

import pytest

from application.dto import DeleteAccountCommand, GetMeCommand, UserResponse
from application.user_use_cases import (
  CognitoClient,
  DeleteAccountUseCase,
  GetMeUseCase,
)
from domain.exceptions import AuthenticationError, DomainValidationError

from .helpers.in_memory_repositories import (
  InMemoryKifuRepository,
  InMemoryTagRepository,
)


class FakeCognitoClient(CognitoClient):
  """Test double for CognitoClient."""

  def __init__(
    self,
    created_at: str = "2024-01-01T00:00:00Z",
    valid_password: str = "correct_password",
  ) -> None:
    self._created_at = created_at
    self._valid_password = valid_password
    self.deleted_users: list[str] = []

  def get_user_created_at(self, username: str) -> str:
    return self._created_at

  def verify_password(self, username: str, password: str) -> None:
    if password != self._valid_password:
      raise AuthenticationError("Invalid password")

  def delete_user(self, username: str) -> None:
    self.deleted_users.append(username)


@pytest.fixture
def cognito_client():
  return FakeCognitoClient()


@pytest.fixture
def kifu_repo():
  return InMemoryKifuRepository()


@pytest.fixture
def tag_repo():
  return InMemoryTagRepository()


class TestGetMeUseCase:
  def test_success(self, cognito_client):
    uc = GetMeUseCase(cognito_client)
    result = uc.execute(GetMeCommand(claims={
      "cognito:username": "testuser",
      "email": "test@example.com",
      "email_verified": "true",
    }))
    assert result.username == "testuser"
    assert result.email == "test@example.com"
    assert result.email_verified is True
    assert result.created_at == "2024-01-01T00:00:00Z"

  def test_email_verified_false(self, cognito_client):
    uc = GetMeUseCase(cognito_client)
    result = uc.execute(GetMeCommand(claims={
      "cognito:username": "testuser",
      "email_verified": "false",
    }))
    assert result.email_verified is False
    assert result.email == ""

  def test_email_verified_boolean_true(self, cognito_client):
    uc = GetMeUseCase(cognito_client)
    result = uc.execute(GetMeCommand(claims={
      "cognito:username": "testuser",
      "email_verified": True,
    }))
    assert result.email_verified is True


class TestDeleteAccountUseCase:
  def test_success(self, cognito_client, kifu_repo, tag_repo):
    uc = DeleteAccountUseCase(cognito_client, kifu_repo, tag_repo)
    uc.execute(DeleteAccountCommand(
      username="testuser", password="correct_password",
    ))
    assert "testuser" in cognito_client.deleted_users

  def test_empty_password(self, cognito_client, kifu_repo, tag_repo):
    uc = DeleteAccountUseCase(cognito_client, kifu_repo, tag_repo)
    with pytest.raises(DomainValidationError, match="password"):
      uc.execute(DeleteAccountCommand(username="testuser", password=""))

  def test_wrong_password(self, cognito_client, kifu_repo, tag_repo):
    uc = DeleteAccountUseCase(cognito_client, kifu_repo, tag_repo)
    with pytest.raises(AuthenticationError, match="Invalid password"):
      uc.execute(DeleteAccountCommand(
        username="testuser", password="wrong_password",
      ))
