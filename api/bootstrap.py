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


def main() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        logger.info("No bootstrap administrator configured")
        return
    if (
        settings.app_env == "production"
        and "replace" in settings.bootstrap_admin_password.casefold()
    ):
        raise RuntimeError("Change BOOTSTRAP_ADMIN_PASSWORD before production startup")
    with SessionLocal() as db:
        username_norm = normalize_username(settings.bootstrap_admin_username)
        if db.scalar(select(User).where(User.username_norm == username_norm)):
            logger.info("Bootstrap administrator already exists")
            return
        user = User(
            username=settings.bootstrap_admin_username.strip(),
            username_norm=username_norm,
            full_name="UGA Stove Administrator",
            password_hash=hash_password(settings.bootstrap_admin_password),
            role=Role.ADMIN,
        )
        db.add(user)
        db.commit()
        logger.info("Bootstrap administrator created")


if __name__ == "__main__":
    main()
