import logging

from sqlalchemy import select

from api.config import get_settings
from api.db import SessionLocal
from api.models import User
from api.normalization import normalize_username
from api.permissions import Role
from api.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uga_stove.bootstrap")

UNSAFE_PASSWORD_MARKERS = (
    "replace",
    "changeme",
    "change-me",
    "password",
    "example",
    "secret",
)


def is_unsafe_bootstrap_password(password: str) -> bool:
    normalized = password.strip().casefold()

    return (
        len(password.strip()) < 16
        or any(marker in normalized for marker in UNSAFE_PASSWORD_MARKERS)
    )


def main() -> None:
    settings = get_settings()
    username = settings.bootstrap_admin_username.strip()
    password = settings.bootstrap_admin_password

    if not username or not password:
        logger.info("No bootstrap administrator configured")
        return

    if settings.app_env == "production" and is_unsafe_bootstrap_password(password):
        raise RuntimeError(
            "Set a strong BOOTSTRAP_ADMIN_PASSWORD of at least 16 characters "
            "before production startup."
        )

    with SessionLocal() as db:
        username_norm = normalize_username(username)
        existing_user = db.scalar(
            select(User).where(User.username_norm == username_norm)
        )

        if existing_user:
            logger.info("Bootstrap administrator already exists")
            return

        user = User(
            username=username,
            username_norm=username_norm,
            full_name="UGA Stove Administrator",
            password_hash=hash_password(password),
            role=Role.ADMIN,
        )
        db.add(user)
        db.commit()
        logger.info("Bootstrap administrator created")


if __name__ == "__main__":
    main()