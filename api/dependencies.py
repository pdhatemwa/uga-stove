from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import User
from api.permissions import Permission, has_permission
from api.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_error from exc
    user = db.get(User, payload.get("sub"))
    if not user or not user.active or user.token_version != payload.get("ver"):
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: Permission) -> Callable:
    def dependency(user: CurrentUser) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=403, detail="You do not have permission for this action"
            )
        return user

    return dependency


def enforce_point_scope(user: User, distribution_point_id: str) -> None:
    if user.distribution_point_id and user.distribution_point_id != distribution_point_id:
        raise HTTPException(
            status_code=403, detail="This record belongs to another distribution point"
        )
