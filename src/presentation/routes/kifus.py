import json

from aws_lambda_powertools.event_handler.api_gateway import Response, Router

from common.auth import get_username

from application.dto import (
  CreateKifuCommand,
  DeleteKifuCommand,
  GetExplorerCommand,
  GetKifuCommand,
  GetRecentKifusCommand,
  RegenerateShareCodeCommand,
  UpdateKifuCommand,
)
from presentation import container

router = Router()


@router.get("/recent")
def get_recent_kifus():
  username = get_username(router)
  uc = container.get_get_recent_kifus_use_case()
  result = uc.execute(GetRecentKifusCommand(username=username))
  return result.to_dict()


@router.post("/")
def create_kifu():
  username = get_username(router)
  body = router.current_event.json_body or {}
  uc = container.get_create_kifu_use_case()
  result = uc.execute(CreateKifuCommand(
    username=username,
    slug=body.get("slug", ""),
    side=body.get("side", "none"),
    result=body.get("result", "none"),
    memo=body.get("memo", ""),
    kif=body.get("kif", ""),
    shared=body.get("shared", False),
    tag_ids=body.get("tag_ids", []),
  ))
  return Response(
    status_code=201,
    content_type="application/json",
    body=json.dumps(result.to_dict()),
  )


@router.get("/explorer")
def get_kifu_explorer():
  username = get_username(router)
  path = router.current_event.get_query_string_value(
    "path", default_value=""
  )
  uc = container.get_get_explorer_use_case()
  result = uc.execute(GetExplorerCommand(username=username, path=path))
  return result.to_dict()


@router.get("/<kid>")
def get_kifu(kid: str):
  username = get_username(router)
  uc = container.get_get_kifu_use_case()
  result = uc.execute(GetKifuCommand(username=username, kid=kid))
  return result.to_dict()


@router.put("/<kid>")
def update_kifu(kid: str):
  username = get_username(router)
  body = router.current_event.json_body or {}
  uc = container.get_update_kifu_use_case()
  result = uc.execute(UpdateKifuCommand(
    username=username,
    kid=kid,
    slug=body.get("slug", ""),
    side=body.get("side", "none"),
    result=body.get("result", "none"),
    memo=body.get("memo", ""),
    kif=body.get("kif", ""),
    shared=body.get("shared", False),
    tag_ids=body.get("tag_ids"),
  ))
  return result.to_dict()


@router.delete("/<kid>")
def delete_kifu(kid: str):
  username = get_username(router)
  uc = container.get_delete_kifu_use_case()
  uc.execute(DeleteKifuCommand(username=username, kid=kid))
  return Response(status_code=204, body="")


@router.put("/<kid>/share-code")
def regenerate_share_code(kid: str):
  username = get_username(router)
  uc = container.get_regenerate_share_code_use_case()
  result = uc.execute(
    RegenerateShareCodeCommand(username=username, kid=kid)
  )
  return result.to_dict()
