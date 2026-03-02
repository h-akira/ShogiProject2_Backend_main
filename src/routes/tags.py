import json

from aws_lambda_powertools.event_handler.api_gateway import Router, Response

from common.auth import get_username
from services import tag_service

router = Router()


@router.get("/")
def get_tags():
  username = get_username(router)
  tags = tag_service.get_tags(username)
  return {"tags": tags}


@router.post("/")
def create_tag():
  username = get_username(router)
  body = router.current_event.json_body or {}
  tag = tag_service.create_tag(username, body)
  return Response(
    status_code=201,
    content_type="application/json",
    body=json.dumps(tag),
  )


@router.get("/<tid>")
def get_tag(tid: str):
  username = get_username(router)
  return tag_service.get_tag(username, tid)


@router.put("/<tid>")
def update_tag(tid: str):
  username = get_username(router)
  body = router.current_event.json_body or {}
  return tag_service.update_tag(username, tid, body)


@router.delete("/<tid>")
def delete_tag(tid: str):
  username = get_username(router)
  tag_service.delete_tag(username, tid)
  return Response(status_code=204, body="")
