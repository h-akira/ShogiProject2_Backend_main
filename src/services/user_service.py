from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from common.config import CLIENT_ID, USER_POOL_ID
from common.exceptions import AuthenticationError, ValidationError
from repositories import kifu_repository, tag_repository
from repositories.db import get_connection


def get_me(claims: dict) -> dict:
  username = claims["cognito:username"]
  email = claims.get("email", "")
  email_verified = claims.get("email_verified", "false")

  client = boto3.client("cognito-idp")
  try:
    user_info = client.admin_get_user(
      UserPoolId=USER_POOL_ID,
      Username=username,
    )
    created_at = user_info["UserCreateDate"].strftime("%Y-%m-%dT%H:%M:%SZ")
  except ClientError:
    created_at = ""

  return {
    "username": username,
    "email": email,
    "email_verified": email_verified in ("true", True),
    "created_at": created_at,
  }


def delete_account(username: str, password: str) -> None:
  if not password:
    raise ValidationError("password is required")

  client = boto3.client("cognito-idp")

  # Verify password via AdminInitiateAuth
  try:
    client.admin_initiate_auth(
      UserPoolId=USER_POOL_ID,
      ClientId=CLIENT_ID,
      AuthFlow="ADMIN_NO_SRP_AUTH",
      AuthParameters={
        "USERNAME": username,
        "PASSWORD": password,
      },
    )
  except ClientError as e:
    if e.response["Error"]["Code"] in (
      "NotAuthorizedException",
      "UserNotFoundException",
    ):
      raise AuthenticationError("Invalid password")
    raise

  # Delete all user data in one transaction
  conn = get_connection()
  with conn.transaction():
    kifu_repository.delete_all_kifu_tags_for_user(username)
    kifu_repository.delete_all_kifus_for_user(username)
    tag_repository.delete_all_tags_for_user(username)

  # Delete Cognito user
  client.admin_delete_user(
    UserPoolId=USER_POOL_ID,
    Username=username,
  )
