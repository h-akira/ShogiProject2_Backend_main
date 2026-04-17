import json

from aws_lambda_powertools.event_handler.api_gateway import Response, Router

from common.auth import get_username

from application.dto import (
  CreateTagCommand,
  DeleteTagCommand,
  GetTagCommand,
  GetTagsCommand,
  UpdateTagCommand,
)
from presentation import container

router = Router()


@router.get("/")
def get_tags():
  username = get_username(router)
  uc = container.get_get_tags_use_case()
  result = uc.execute(GetTagsCommand(username=username))
  return {"tags": [t.to_dict() for t in result]}


@router.post("/")
def create_tag():
  username = get_username(router)
  body = router.current_event.json_body or {}
  uc = container.get_create_tag_use_case()
  result = uc.execute(CreateTagCommand(
    username=username,
    name=body.get("name", ""),
  ))
  return Response(
    status_code=201,
    content_type="application/json",
    body=json.dumps(result.to_dict()),
  )


@router.get("/<tid>")
def get_tag(tid: str):
  username = get_username(router)
  uc = container.get_get_tag_use_case()
  result = uc.execute(GetTagCommand(username=username, tid=tid))
  return result.to_dict()


@router.put("/<tid>")
def update_tag(tid: str):
  username = get_username(router)
  body = router.current_event.json_body or {}
  uc = container.get_update_tag_use_case()
  result = uc.execute(UpdateTagCommand(
    username=username,
    tid=tid,
    name=body.get("name", ""),
  ))
  return result.to_dict()


@router.delete("/<tid>")
def delete_tag(tid: str):
  username = get_username(router)
  uc = container.get_delete_tag_use_case()
  uc.execute(DeleteTagCommand(username=username, tid=tid))
  return Response(status_code=204, body="")
