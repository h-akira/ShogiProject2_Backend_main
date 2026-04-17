"""Cognito client implementation.

Implements the CognitoClient ABC defined in the application layer.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from application.user_use_cases import CognitoClient
from domain.exceptions import AuthenticationError


class AwsCognitoClient(CognitoClient):
  """AWS Cognito implementation using boto3."""

  def __init__(self, user_pool_id: str, client_id: str) -> None:
    self._user_pool_id = user_pool_id
    self._client_id = client_id
    self._client = boto3.client("cognito-idp")

  def get_user_created_at(self, username: str) -> str:
    try:
      user_info = self._client.admin_get_user(
        UserPoolId=self._user_pool_id,
        Username=username,
      )
      return user_info["UserCreateDate"].strftime("%Y-%m-%dT%H:%M:%SZ")
    except ClientError:
      return ""

  def verify_password(self, username: str, password: str) -> None:
    try:
      self._client.admin_initiate_auth(
        UserPoolId=self._user_pool_id,
        ClientId=self._client_id,
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

  def delete_user(self, username: str) -> None:
    self._client.admin_delete_user(
      UserPoolId=self._user_pool_id,
      Username=username,
    )
