import secrets
import string

_ALPHABET = string.ascii_letters + string.digits


def generate_id(length: int = 12) -> str:
  return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def generate_share_code(length: int = 36) -> str:
  return "".join(secrets.choice(_ALPHABET) for _ in range(length))
