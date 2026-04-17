"""Exception handlers mapping domain exceptions to HTTP responses."""

from __future__ import annotations

import json

from aws_lambda_powertools.event_handler import Response

from domain.exceptions import (
  AuthenticationError,
  ConflictError,
  DomainError,
  DomainValidationError,
  EntityNotFoundError,
  LimitExceededError,
)

# Maps domain exception types to HTTP status codes
_STATUS_MAP: dict[type, int] = {
  DomainValidationError: 400,
  LimitExceededError: 400,
  EntityNotFoundError: 404,
  ConflictError: 409,
  AuthenticationError: 403,
}


def handle_domain_error(ex: DomainError) -> Response:
  """Convert a domain exception to an HTTP response."""
  status_code = _STATUS_MAP.get(type(ex), 500)
  return Response(
    status_code=status_code,
    content_type="application/json",
    body=json.dumps({"message": ex.message}),
  )
