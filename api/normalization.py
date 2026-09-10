import re
import unicodedata

IDENTIFIER_PATTERN = re.compile(r"[^A-Z0-9]+")
SPACE_PATTERN = re.compile(r"\s+")


def normalize_identifier(value: str) -> str:
    """Canonical comparison form used by database uniqueness constraints."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = IDENTIFIER_PATTERN.sub("", ascii_value.upper())
    if not normalized:
        raise ValueError("Identifier cannot be empty")
    return normalized


def normalize_username(value: str) -> str:
    normalized = SPACE_PATTERN.sub("", value.strip().lower())
    if not normalized:
        raise ValueError("Username cannot be empty")
    return normalized


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = SPACE_PATTERN.sub(" ", value).strip()
    return cleaned or None
