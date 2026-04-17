"""User-related use cases.

User is not a domain entity in this bounded context — it is an
external identity managed by Cognito. These use cases coordinate
Cognito operations and data cleanup.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.exceptions import AuthenticationError, DomainValidationError
from domain.repositories import KifuRepository, TagRepository
from domain.value_objects import Username

from application.dto import (
  DeleteAccountCommand,
  GetMeCommand,
  UserResponse,
)


class CognitoClient(ABC):
  """Abstract interface for Cognito operations.

  Implementation lives in the infrastructure layer.
  """

  @abstractmethod
  def get_user_created_at(self, username: str) -> str:
    """Get user creation date as ISO 8601 string."""
    ...

  @abstractmethod
  def verify_password(self, username: str, password: str) -> None:
    """Verify user password. Raises AuthenticationError on failure."""
    ...

  @abstractmethod
  def delete_user(self, username: str) -> None:
    """Delete user from Cognito."""
    ...


class GetMeUseCase:
  def __init__(self, cognito_client: CognitoClient) -> None:
    self._cognito_client = cognito_client

  def execute(self, command: GetMeCommand) -> UserResponse:
    claims = command.claims
    username = claims["cognito:username"]
    email = claims.get("email", "")
    email_verified = claims.get("email_verified", "false")

    created_at = self._cognito_client.get_user_created_at(username)

    return UserResponse(
      username=username,
      email=email,
      email_verified=email_verified in ("true", True),
      created_at=created_at,
    )


class DeleteAccountUseCase:
  def __init__(
    self,
    cognito_client: CognitoClient,
    kifu_repo: KifuRepository,
    tag_repo: TagRepository,
  ) -> None:
    self._cognito_client = cognito_client
    self._kifu_repo = kifu_repo
    self._tag_repo = tag_repo

  def execute(self, command: DeleteAccountCommand) -> None:
    if not command.password:
      raise DomainValidationError("password is required")

    username = Username(command.username)

    # Verify password
    self._cognito_client.verify_password(
      command.username, command.password
    )

    # Delete all user data
    self._kifu_repo.delete_all_for_user(username)
    self._tag_repo.delete_all_for_user(username)

    # Delete Cognito user
    self._cognito_client.delete_user(command.username)
