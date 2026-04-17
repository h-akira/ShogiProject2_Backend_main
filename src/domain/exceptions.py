"""Domain exceptions.

These exceptions carry no HTTP status codes. The presentation layer
is responsible for mapping them to appropriate HTTP responses.
"""


class DomainError(Exception):
  """Base class for all domain exceptions."""

  def __init__(self, message: str = "Domain error"):
    self.message = message
    super().__init__(self.message)


class DomainValidationError(DomainError):
  """Raised when a domain invariant or input validation fails."""

  def __init__(self, message: str = "Validation error"):
    super().__init__(message)


class EntityNotFoundError(DomainError):
  """Raised when a requested entity does not exist."""

  def __init__(self, message: str = "Entity not found"):
    super().__init__(message)


class ConflictError(DomainError):
  """Raised when a uniqueness constraint is violated."""

  def __init__(self, message: str = "Resource already exists"):
    super().__init__(message)


class LimitExceededError(DomainError):
  """Raised when a per-user resource limit is exceeded."""

  def __init__(self, message: str = "Limit exceeded"):
    super().__init__(message)


class AuthenticationError(DomainError):
  """Raised when authentication fails (e.g., wrong password)."""

  def __init__(self, message: str = "Authentication failed"):
    super().__init__(message)
