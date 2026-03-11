"""Route layer integration tests.

Uses mock to mock service layer functions, so PostgreSQL is not required.
Tests the full request/response flow through Lambda Powertools.
"""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from tests.local.conftest import make_apigw_event


class TestUserRoutes:
  def test_get_me_200(self, aws_mock):
    from services import user_service

    with patch.object(user_service, "get_me") as mock_get_me:
      mock_get_me.return_value = {
        "username": "testuser",
        "email": "testuser@example.com",
        "email_verified": True,
        "created_at": "2025-01-15T09:30:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event("GET", "/api/v1/main/users/me", username="testuser")
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert body["username"] == "testuser"


class TestKifuRoutes:
  def test_create_kifu_201(self):
    from services import kifu_service

    with patch.object(kifu_service, "create_kifu") as mock_create:
      mock_create.return_value = {
        "kid": "kid_test0001",
        "slug": "game.kif",
        "side": "sente",
        "result": "win",
        "tags": [],
        "memo": "",
        "shared": False,
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "POST",
        "/api/v1/main/kifus",
        body={"slug": "game", "side": "sente", "result": "win", "kif": "data"},
        username="testuser",
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 201
      body = json.loads(response["body"])
      assert body["kid"] == "kid_test0001"

  def test_get_recent_kifus_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "get_recent_kifus") as mock_recent:
      mock_recent.return_value = {
        "kifus": [
          {"kid": "k1", "slug": "g1.kif", "side": "none", "result": "none", "tags": [], "updated_at": "2025-01-15T09:30:00Z"},
        ],
        "total_count": 1,
      }

      from app import lambda_handler
      event = make_apigw_event("GET", "/api/v1/main/kifus/recent", username="testuser")
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert "kifus" in body
      assert body["total_count"] == 1

  def test_get_kifu_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "get_kifu") as mock_get:
      mock_get.return_value = {
        "kid": "kid_get00001",
        "slug": "game.kif",
        "side": "sente",
        "result": "win",
        "tags": [],
        "memo": "",
        "shared": False,
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/kifus/kid_get00001",
        username="testuser",
        path_params={"kid": "kid_get00001"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert body["kid"] == "kid_get00001"

  def test_get_kifu_404(self):
    from services import kifu_service
    from common.exceptions import NotFoundError

    with patch.object(kifu_service, "get_kifu") as mock_get:
      mock_get.side_effect = NotFoundError("Kifu not found")

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/kifus/nonexistent",
        username="testuser",
        path_params={"kid": "nonexistent"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 404
      body = json.loads(response["body"])
      assert "message" in body

  def test_update_kifu_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "update_kifu") as mock_update:
      mock_update.return_value = {
        "kid": "kid_upd00001",
        "slug": "updated.kif",
        "side": "gote",
        "result": "loss",
        "tags": [],
        "memo": "",
        "shared": False,
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "PUT",
        "/api/v1/main/kifus/kid_upd00001",
        body={"slug": "updated", "side": "gote", "result": "loss", "kif": "data"},
        username="testuser",
        path_params={"kid": "kid_upd00001"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200

  def test_delete_kifu_204(self):
    from services import kifu_service

    with patch.object(kifu_service, "delete_kifu") as mock_delete:
      mock_delete.return_value = None

      from app import lambda_handler
      event = make_apigw_event(
        "DELETE",
        "/api/v1/main/kifus/kid_del00001",
        username="testuser",
        path_params={"kid": "kid_del00001"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 204

  def test_get_explorer_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "get_explorer") as mock_explorer:
      mock_explorer.return_value = {
        "path": "",
        "folders": [{"name": "folder1", "count": 3}],
        "files": [{"kid": "k1", "name": "game.kif"}],
      }

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/kifus/explorer",
        username="testuser",
        query_params={"path": ""},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert "folders" in body
      assert "files" in body

  def test_regenerate_share_code_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "regenerate_share_code") as mock_regen:
      mock_regen.return_value = {"share_code": "new_code_123"}

      from app import lambda_handler
      event = make_apigw_event(
        "PUT",
        "/api/v1/main/kifus/kid_rsc00001/share-code",
        username="testuser",
        path_params={"kid": "kid_rsc00001"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert body["share_code"] == "new_code_123"

  def test_create_kifu_400_invalid(self):
    from services import kifu_service
    from common.exceptions import ValidationError

    with patch.object(kifu_service, "create_kifu") as mock_create:
      mock_create.side_effect = ValidationError("slug must be 1-255 characters")

      from app import lambda_handler
      event = make_apigw_event(
        "POST",
        "/api/v1/main/kifus",
        body={"slug": "", "side": "none", "result": "none", "kif": ""},
        username="testuser",
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 400

  def test_create_kifu_409_conflict(self):
    from services import kifu_service
    from common.exceptions import ConflictError

    with patch.object(kifu_service, "create_kifu") as mock_create:
      mock_create.side_effect = ConflictError("slug 'game.kif' already exists")

      from app import lambda_handler
      event = make_apigw_event(
        "POST",
        "/api/v1/main/kifus",
        body={"slug": "game", "side": "none", "result": "none", "kif": "data"},
        username="testuser",
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 409


class TestSharedRoutes:
  def test_get_shared_kifu_200(self):
    from services import kifu_service

    with patch.object(kifu_service, "get_shared_kifu") as mock_shared:
      mock_shared.return_value = {
        "slug": "shared.kif",
        "side": "sente",
        "result": "win",
        "memo": "memo",
        "kif": "data",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/shared/sharecode123",
        path_params={"share_code": "sharecode123"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert body["slug"] == "shared.kif"

  def test_get_shared_kifu_404(self):
    from services import kifu_service
    from common.exceptions import NotFoundError

    with patch.object(kifu_service, "get_shared_kifu") as mock_shared:
      mock_shared.side_effect = NotFoundError("Shared kifu not found")

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/shared/nonexistent",
        path_params={"share_code": "nonexistent"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 404


class TestTagRoutes:
  def test_create_tag_201(self):
    from services import tag_service

    with patch.object(tag_service, "create_tag") as mock_create:
      mock_create.return_value = {
        "tid": "tid_test0001",
        "name": "Test Tag",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "POST",
        "/api/v1/main/tags",
        body={"name": "Test Tag"},
        username="testuser",
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 201
      body = json.loads(response["body"])
      assert body["tid"] == "tid_test0001"

  def test_get_tags_200(self):
    from services import tag_service

    with patch.object(tag_service, "get_tags") as mock_tags:
      mock_tags.return_value = [
        {"tid": "t1", "name": "Tag A", "created_at": "2025-01-15T09:30:00Z", "updated_at": "2025-01-15T09:30:00Z"},
      ]

      from app import lambda_handler
      event = make_apigw_event("GET", "/api/v1/main/tags", username="testuser")
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200
      body = json.loads(response["body"])
      assert "tags" in body

  def test_get_tag_200(self):
    from services import tag_service

    with patch.object(tag_service, "get_tag") as mock_tag:
      mock_tag.return_value = {
        "tid": "t1",
        "name": "Tag",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T09:30:00Z",
        "kifus": [],
      }

      from app import lambda_handler
      event = make_apigw_event(
        "GET",
        "/api/v1/main/tags/t1",
        username="testuser",
        path_params={"tid": "t1"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200

  def test_update_tag_200(self):
    from services import tag_service

    with patch.object(tag_service, "update_tag") as mock_update:
      mock_update.return_value = {
        "tid": "t1",
        "name": "Updated",
        "created_at": "2025-01-15T09:30:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
      }

      from app import lambda_handler
      event = make_apigw_event(
        "PUT",
        "/api/v1/main/tags/t1",
        body={"name": "Updated"},
        username="testuser",
        path_params={"tid": "t1"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 200

  def test_delete_tag_204(self):
    from services import tag_service

    with patch.object(tag_service, "delete_tag") as mock_delete:
      mock_delete.return_value = None

      from app import lambda_handler
      event = make_apigw_event(
        "DELETE",
        "/api/v1/main/tags/t1",
        username="testuser",
        path_params={"tid": "t1"},
      )
      response = lambda_handler(event, None)

      assert response["statusCode"] == 204
