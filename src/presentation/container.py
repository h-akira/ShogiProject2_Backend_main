"""Dependency Injection container.

Wires infrastructure implementations to application use cases.
Instances are created lazily and cached for the Lambda execution context.
"""

from __future__ import annotations

from common.config import CLIENT_ID, KIFU_MAX, TAG_MAX, USER_POOL_ID
from infrastructure.cognito_client import AwsCognitoClient
from infrastructure.db import get_connection
from infrastructure.kifu_repository import PostgresKifuRepository
from infrastructure.tag_repository import PostgresTagRepository

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
from application.tag_use_cases import (
  CreateTagUseCase,
  DeleteTagUseCase,
  GetTagsUseCase,
  GetTagUseCase,
  UpdateTagUseCase,
)
from application.user_use_cases import DeleteAccountUseCase, GetMeUseCase

# -- Singleton repositories (created once per Lambda cold start) --

_kifu_repo: PostgresKifuRepository | None = None
_tag_repo: PostgresTagRepository | None = None
_cognito_client: AwsCognitoClient | None = None


def _get_kifu_repo() -> PostgresKifuRepository:
  global _kifu_repo
  if _kifu_repo is None:
    _kifu_repo = PostgresKifuRepository(get_connection)
  return _kifu_repo


def _get_tag_repo() -> PostgresTagRepository:
  global _tag_repo
  if _tag_repo is None:
    _tag_repo = PostgresTagRepository(get_connection)
  return _tag_repo


def _get_cognito_client() -> AwsCognitoClient:
  global _cognito_client
  if _cognito_client is None:
    _cognito_client = AwsCognitoClient(USER_POOL_ID, CLIENT_ID)
  return _cognito_client


# -- Kifu Use Cases --

def get_create_kifu_use_case() -> CreateKifuUseCase:
  return CreateKifuUseCase(_get_kifu_repo(), _get_tag_repo(), KIFU_MAX)


def get_get_kifu_use_case() -> GetKifuUseCase:
  return GetKifuUseCase(_get_kifu_repo())


def get_get_recent_kifus_use_case() -> GetRecentKifusUseCase:
  return GetRecentKifusUseCase(_get_kifu_repo())


def get_get_explorer_use_case() -> GetExplorerUseCase:
  return GetExplorerUseCase(_get_kifu_repo())


def get_update_kifu_use_case() -> UpdateKifuUseCase:
  return UpdateKifuUseCase(_get_kifu_repo(), _get_tag_repo())


def get_delete_kifu_use_case() -> DeleteKifuUseCase:
  return DeleteKifuUseCase(_get_kifu_repo())


def get_get_shared_kifu_use_case() -> GetSharedKifuUseCase:
  return GetSharedKifuUseCase(_get_kifu_repo())


def get_regenerate_share_code_use_case() -> RegenerateShareCodeUseCase:
  return RegenerateShareCodeUseCase(_get_kifu_repo())


# -- Tag Use Cases --

def get_create_tag_use_case() -> CreateTagUseCase:
  return CreateTagUseCase(_get_tag_repo(), TAG_MAX)


def get_get_tags_use_case() -> GetTagsUseCase:
  return GetTagsUseCase(_get_tag_repo())


def get_get_tag_use_case() -> GetTagUseCase:
  return GetTagUseCase(_get_tag_repo())


def get_update_tag_use_case() -> UpdateTagUseCase:
  return UpdateTagUseCase(_get_tag_repo())


def get_delete_tag_use_case() -> DeleteTagUseCase:
  return DeleteTagUseCase(_get_tag_repo())


# -- User Use Cases --

def get_get_me_use_case() -> GetMeUseCase:
  return GetMeUseCase(_get_cognito_client())


def get_delete_account_use_case() -> DeleteAccountUseCase:
  return DeleteAccountUseCase(
    _get_cognito_client(), _get_kifu_repo(), _get_tag_repo()
  )
