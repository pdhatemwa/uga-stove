from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from api.audit import audit_event
from api.dependencies import CurrentUser, DbSession
from api.models import User
from api.normalization import normalize_username
from api.schemas import PasswordChange, TokenOut, UserOut
from api.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = db.scalar(select(User).where(User.username_norm == normalize_username(form.username)))
    if not user or not user.active or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.now(UTC)
    db.commit()
    token, expires_in = create_access_token(user.id, user.token_version)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/change-password", status_code=204)
def change_password(
    payload: PasswordChange,
    request: Request,
    user: CurrentUser,
    db: DbSession,
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    audit_event(
        db,
        actor=user,
        action="user.password_changed",
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    db.commit()
    return None
