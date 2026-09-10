import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from api.dependencies import DbSession, require_permission
from api.models import Distribution, Household, User
from api.normalization import normalize_identifier
from api.pdfs import build_record_pdf
from api.permissions import Permission
from api.schemas import DuplicateCheckOut, RecordCreate, RecordOut, RecordUpdate
from api.services import (
    create_record,
    duplicate_check,
    get_record_by_code,
    get_record_by_uid,
    record_to_schema,
    update_record,
)

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/check", response_model=DuplicateCheckOut)
def check_duplicates(
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_CREATE))],
    household_uid: str | None = Query(default=None),
    serial_number: str | None = Query(default=None),
):
    return duplicate_check(db, household_uid, serial_number)


@router.post("", response_model=RecordOut, status_code=201)
def add_record(
    payload: RecordCreate,
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_CREATE))],
):
    return record_to_schema(create_record(db, payload, user, request))


@router.get("/export.csv")
def export_records(
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_EXPORT))],
):
    statement = (
        select(Distribution)
        .join(Distribution.household)
        .options(
            joinedload(Distribution.household),
            joinedload(Distribution.stove),
            joinedload(Distribution.distribution_point),
        )
        .order_by(Distribution.distributed_on, Household.household_uid)
    )
    if user.distribution_point_id:
        statement = statement.where(
            Distribution.distribution_point_id == user.distribution_point_id
        )
    records = db.scalars(statement).unique().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "household_uid",
            "household_head_name",
            "household_size",
            "phone_number",
            "district",
            "subcounty",
            "parish",
            "village",
            "distribution_point",
            "serial_number",
            "stove_size",
            "distributed_on",
            "receiver_type",
            "receiver_name",
            "ambassador_name",
            "signature_status",
            "verification_code",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.household.household_uid,
                record.household.household_head_name,
                record.household.household_size,
                record.household.phone_number,
                record.household.district,
                record.household.subcounty,
                record.household.parish,
                record.household.village,
                record.distribution_point.name,
                record.stove.serial_number,
                record.stove.stove_size,
                record.distributed_on.isoformat(),
                record.receiver_type,
                record.receiver_name or "",
                record.ambassador_name,
                record.signature_status.value,
                record.verification_code,
            ]
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=uga_stove_export.csv"},
    )


@router.get("/verify/{verification_code}", response_model=RecordOut)
def verify_record(
    verification_code: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_VIEW))],
):
    return record_to_schema(get_record_by_code(db, verification_code, user))


@router.get("/{household_uid}", response_model=RecordOut)
def fetch_record(
    household_uid: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_VIEW))],
):
    return record_to_schema(get_record_by_uid(db, household_uid, user))


@router.patch("/{household_uid}", response_model=RecordOut)
def edit_record(
    household_uid: str,
    payload: RecordUpdate,
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_UPDATE))],
):
    record = get_record_by_uid(db, household_uid, user)
    return record_to_schema(update_record(db, record, payload, user, request))


@router.get("/{household_uid}/form.pdf")
def print_form(
    household_uid: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.PDF_PRINT))],
):
    record = get_record_by_uid(db, household_uid, user)
    pdf = build_record_pdf(record)
    safe_uid = normalize_identifier(record.household.household_uid)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="UGA-Stove-{safe_uid}.pdf"'},
    )
