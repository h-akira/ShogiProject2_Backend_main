from aws_lambda_powertools.event_handler.api_gateway import Response, Router

from common.auth import get_username

from application.dto import DeleteAccountCommand, GetMeCommand
from presentation import container

router = Router()


@router.get("/me")
def get_me():
  claims = router.current_event.request_context.authorizer.claims
  uc = container.get_get_me_use_case()
  result = uc.execute(GetMeCommand(claims=claims))
  return result.to_dict()


@router.delete("/me")
def delete_me():
  username = get_username(router)
  body = router.current_event.json_body or {}
  password = body.get("password", "")
  uc = container.get_delete_account_use_case()
  uc.execute(DeleteAccountCommand(username=username, password=password))
  return Response(status_code=204, body="")
