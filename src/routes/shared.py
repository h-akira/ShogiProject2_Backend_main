from aws_lambda_powertools.event_handler.api_gateway import Router

from services import kifu_service

router = Router()


@router.get("/<share_code>")
def get_shared_kifu(share_code: str):
  return kifu_service.get_shared_kifu(share_code)
