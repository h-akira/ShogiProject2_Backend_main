class AppError(Exception):
  """Base application error."""
  status_code: int = 500

  def __init__(self, message: str = "Internal server error"):
    self.message = message
    super().__init__(self.message)


class NotFoundError(AppError):
  status_code = 404

  def __init__(self, message: str = "Resource not found"):
    super().__init__(message)


class ValidationError(AppError):
  status_code = 400

  def __init__(self, message: str = "Validation error"):
    super().__init__(message)


class ConflictError(AppError):
  status_code = 409

  def __init__(self, message: str = "Resource already exists"):
    super().__init__(message)


class LimitExceededError(AppError):
  status_code = 400

  def __init__(self, message: str = "Limit exceeded"):
    super().__init__(message)


class AuthenticationError(AppError):
  status_code = 403

  def __init__(self, message: str = "Authentication failed"):
    super().__init__(message)
