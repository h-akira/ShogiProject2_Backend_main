import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response

from domain.exceptions import DomainError
from presentation.exception_handlers import handle_domain_error
from presentation.routes.users import router as users_router
from presentation.routes.kifus import router as kifus_router
from presentation.routes.shared import router as shared_router
from presentation.routes.tags import router as tags_router

logger = Logger()
tracer = Tracer()

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


@app.exception_handler(DomainError)
def handle_domain_exception(ex: DomainError):
  return handle_domain_error(ex)


@app.exception_handler(ValueError)
def handle_value_error(ex: ValueError):
  return Response(
    status_code=400,
    content_type="application/json",
    body=json.dumps({"message": str(ex)}),
  )


@app.exception_handler(Exception)
def handle_unexpected_error(ex: Exception):
  logger.exception("Unexpected error")
  return Response(
    status_code=500,
    content_type="application/json",
    body=json.dumps({"message": "Internal server error"}),
  )


@tracer.capture_lambda_handler
def lambda_handler(event, context):
  return app.resolve(event, context)
