import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response

from common.exceptions import AppError
from routes.users import router as users_router
from routes.kifus import router as kifus_router
from routes.shared import router as shared_router
from routes.tags import router as tags_router

logger = Logger()

app = APIGatewayRestResolver(
  strip_prefixes=["/api/v1/main"],
  cors=CORSConfig(
    allow_origin="*",
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
  ),
)

app.include_router(users_router, prefix="/users")
app.include_router(kifus_router, prefix="/kifus")
app.include_router(shared_router, prefix="/shared")
app.include_router(tags_router, prefix="/tags")


@app.exception_handler(AppError)
def handle_app_error(ex: AppError):
  return Response(
    status_code=ex.status_code,
    content_type="application/json",
    body=json.dumps({"message": ex.message}),
  )


@app.exception_handler(Exception)
def handle_unexpected_error(ex: Exception):
  logger.exception("Unexpected error")
  return Response(
    status_code=500,
    content_type="application/json",
    body=json.dumps({"message": "Internal server error"}),
  )


def lambda_handler(event, context):
  return app.resolve(event, context)
