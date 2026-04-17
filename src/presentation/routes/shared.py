from aws_lambda_powertools.event_handler.api_gateway import Router

from application.dto import GetSharedKifuCommand
from presentation import container

router = Router()


@router.get("/<share_code>")
def get_shared_kifu(share_code: str):
  uc = container.get_get_shared_kifu_use_case()
  result = uc.execute(GetSharedKifuCommand(share_code=share_code))
  return result.to_dict()
