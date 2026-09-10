import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.audit import audit_event
from api.dependencies import DbSession, require_permission
from api.importers.kobo_csv import import_kobo_csv, parse_point_mapping
from api.models import AuditLog, DistributionPoint, User
from api.normalization import normalize_username
from api.permissions import Permission
from api.schemas import (
    AuditOut,
    DistributionPointCreate,
    DistributionPointOut,
    UserCreate,
    UserOut,
)
from api.security import hash_password

router = APIRouter(prefix="/admin", tags=["administration"])


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: DbSession,
    actor: Annotated[User, Depends(require_permission(Permission.USER_MANAGE))],
):
    if payload.distribution_point_id:
        point = db.get(DistributionPoint, payload.distribution_point_id)
        if not point or not point.active:
            raise HTTPException(status_code=400, detail="Assigned distribution point is not active")
    user = User(
        username=payload.username.strip(),
        username_norm=normalize_username(payload.username),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        distribution_point_id=payload.distribution_point_id,
    )
    db.add(user)
    try:
        db.flush()
        audit_event(
            db,
            actor=actor,
            action="user.created",
            entity_type="user",
            entity_id=user.id,
            after={"username": user.username, "role": user.role.value},
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: DbSession,
    actor: Annotated[User, Depends(require_permission(Permission.USER_MANAGE))],
):
    return db.scalars(select(User).order_by(User.full_name)).all()


@router.post("/distribution-points", response_model=DistributionPointOut, status_code=201)
def create_distribution_point(
    payload: DistributionPointCreate,
    request: Request,
    db: DbSession,
    actor: Annotated[User, Depends(require_permission(Permission.POINT_MANAGE))],
):
    code = re.sub(r"[^A-Z0-9]+", "-", payload.code.strip().upper()).strip("-")
    point = DistributionPoint(code=code, name=payload.name.strip())
    db.add(point)
    try:
        db.flush()
        audit_event(
            db,
            actor=actor,
            action="distribution_point.created",
            entity_type="distribution_point",
            entity_id=point.id,
            after={"code": point.code, "name": point.name},
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Distribution point code already exists"
        ) from exc
    return point


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    db: DbSession,
    actor: Annotated[User, Depends(require_permission(Permission.AUDIT_VIEW))],
    limit: int = 200,
):
    limit = min(max(limit, 1), 1000)
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()


@router.post("/imports/kobo")
async def import_kobo(
    db: DbSession,
    actor: Annotated[User, Depends(require_permission(Permission.IMPORT_RUN))],
    source: UploadFile = File(...),
    point_mapping: UploadFile = File(...),
    commit: bool = Form(default=False),
):
    raw = await source.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Import file exceeds 20 MB")
    mapping_raw = await point_mapping.read(1024 * 1024)
    try:
        mapping = parse_point_mapping(mapping_raw)
        result = import_kobo_csv(
            db,
            csv_bytes=raw,
            source_filename=source.filename or "kobo-export.csv",
            actor=actor,
            point_mapping=mapping,
            commit=commit,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.to_dict()
