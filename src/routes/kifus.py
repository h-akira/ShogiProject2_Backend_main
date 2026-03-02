import json

from aws_lambda_powertools.event_handler.api_gateway import Router, Response

from common.auth import get_username
from services import kifu_service

router = Router()


@router.get("/recent")
def get_recent_kifus():
  username = get_username(router)
  return kifu_service.get_recent_kifus(username)


@router.post("/")
def create_kifu():
  username = get_username(router)
  body = router.current_event.json_body or {}
  kifu = kifu_service.create_kifu(username, body)
  return Response(
    status_code=201,
    content_type="application/json",
    body=json.dumps(kifu),
  )


@router.get("/explorer")
def get_kifu_explorer():
  username = get_username(router)
  path = router.current_event.get_query_string_value("path", default_value="")
  return kifu_service.get_explorer(username, path)


@router.get("/<kid>")
def get_kifu(kid: str):
  username = get_username(router)
  return kifu_service.get_kifu(username, kid)


@router.put("/<kid>")
def update_kifu(kid: str):
  username = get_username(router)
  body = router.current_event.json_body or {}
  return kifu_service.update_kifu(username, kid, body)


@router.delete("/<kid>")
def delete_kifu(kid: str):
  username = get_username(router)
  kifu_service.delete_kifu(username, kid)
  return Response(status_code=204, body="")


@router.put("/<kid>/share-code")
def regenerate_share_code(kid: str):
  username = get_username(router)
  return kifu_service.regenerate_share_code(username, kid)
