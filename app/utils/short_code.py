import secrets
import string

from app.config import get_settings

settings = get_settings()

# Characters used for generating short codes (alphanumeric, URL-safe)
ALPHABET = string.ascii_letters + string.digits


def generate_short_code(length: int | None = None) -> str:
    """Generate a random short code."""
    if length is None:
        length = settings.short_code_length
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
