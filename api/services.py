import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from api.audit import audit_event, record_snapshot
from api.dependencies import enforce_point_scope
from api.models import Distribution, DistributionPoint, Household, Stove, User
from api.normalization import normalize_identifier
from api.permissions import Permission, has_permission
from api.schemas import (
    DistributionPointOut,
    DuplicateCheckOut,
    HouseholdOut,
    RecordCreate,
    RecordOut,
    RecordUpdate,
    SignatureEvidenceOut,
    StoveOut,
)


def _record_query():
    return (
        select(Distribution)
        .options(
            joinedload(Distribution.household),
            joinedload(Distribution.stove),
            joinedload(Distribution.distribution_point),
            selectinload(Distribution.signature_evidence),
        )
        .execution_options(populate_existing=True)
    )


def get_record_by_uid(db: Session, household_uid: str, user: User) -> Distribution:
    uid_norm = normalize_identifier(household_uid)
    record = db.scalar(
        _record_query().join(Distribution.household).where(Household.household_uid_norm == uid_norm)
    )
    if not record:
        raise HTTPException(status_code=404, detail="Household ID was not found")
    enforce_point_scope(user, record.distribution_point_id)
    return record


def get_record_by_code(db: Session, verification_code: str, user: User) -> Distribution:
    record = db.scalar(
        _record_query().where(
            Distribution.verification_code == normalize_identifier(verification_code)
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="Verification code was not found")
    enforce_point_scope(user, record.distribution_point_id)
    return record


def duplicate_check(
    db: Session, household_uid: str | None, serial_number: str | None
) -> DuplicateCheckOut:
    household_exists = False
    serial_exists = False
    if household_uid:
        household_exists = (
            db.scalar(
                select(func.count(Household.id)).where(
                    Household.household_uid_norm == normalize_identifier(household_uid)
                )
            )
            > 0
        )
    if serial_number:
        serial_exists = (
            db.scalar(
                select(func.count(Stove.id)).where(
                    Stove.serial_number_norm == normalize_identifier(serial_number)
                )
            )
            > 0
        )
    messages = []
    if household_exists:
        messages.append("Household ID already exists")
    if serial_exists:
        messages.append("Stove serial number already exists")
    return DuplicateCheckOut(
        household_exists=household_exists,
        serial_exists=serial_exists,
        message=". ".join(messages) or None,
    )


def _new_verification_code(db: Session) -> str:
    for _ in range(10):
        code = f"UGA{secrets.token_hex(5).upper()}"
        exists = db.scalar(
            select(func.count(Distribution.id)).where(Distribution.verification_code == code)
        )
        if not exists:
            return code
    raise RuntimeError("Could not allocate a unique verification code")


def create_record(db: Session, payload: RecordCreate, user: User, request=None) -> Distribution:
    enforce_point_scope(user, payload.distribution_point_id)
    point = db.get(DistributionPoint, payload.distribution_point_id)
    if not point or not point.active:
        raise HTTPException(status_code=400, detail="Select an active distribution point")

    conflicts = duplicate_check(db, payload.household_uid, payload.serial_number)
    if conflicts.household_exists or conflicts.serial_exists:
        raise HTTPException(status_code=409, detail=conflicts.message)

    household = Household(
        household_uid=payload.household_uid,
        household_uid_norm=normalize_identifier(payload.household_uid),
        household_head_name=payload.household_head_name,
        family_name=payload.family_name,
        household_size=payload.household_size,
        phone_number=payload.phone_number,
        additional_contact=payload.additional_contact,
        district=payload.district,
        subcounty=payload.subcounty,
        parish=payload.parish,
        village=payload.village,
        latitude=payload.latitude,
        longitude=payload.longitude,
        altitude_m=payload.altitude_m,
        gps_precision_m=payload.gps_precision_m,
        existing_stove_type_1=payload.existing_stove_type_1,
        existing_stove_type_2=payload.existing_stove_type_2,
        fuel_type=payload.fuel_type,
        fuel_amount_per_week=payload.fuel_amount_per_week,
        existing_stove_units=payload.existing_stove_units,
        existing_stoves_removed=payload.existing_stoves_removed,
        created_by_user_id=user.id,
    )
    stove = Stove(
        serial_number=payload.serial_number,
        serial_number_norm=normalize_identifier(payload.serial_number),
        stove_type=payload.stove_type,
        stove_size=payload.stove_size,
        created_by_user_id=user.id,
    )
    distribution = Distribution(
        household=household,
        stove=stove,
        distribution_point=point,
        distributed_on=payload.distributed_on,
        receiver_type=payload.receiver_type,
        receiver_name=payload.receiver_name,
        receiver_relationship=payload.receiver_relationship,
        carbon_waiver_accepted=payload.carbon_waiver_accepted,
        conditions_accepted=payload.conditions_accepted,
        ambassador_name=payload.ambassador_name,
        verification_code=_new_verification_code(db),
        legacy_source=payload.legacy_source,
        legacy_record_id=payload.legacy_record_id,
        legacy_uuid=payload.legacy_uuid,
        legacy_photo_url=payload.legacy_photo_url,
        created_by_user_id=user.id,
    )
    db.add(distribution)
    try:
        db.flush()
        audit_event(
            db,
            actor=user,
            action="record.created",
            entity_type="distribution",
            entity_id=distribution.id,
            after=record_snapshot(distribution),
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        conflicts = duplicate_check(db, payload.household_uid, payload.serial_number)
        message = conflicts.message or "Record conflicts with an existing unique value"
        raise HTTPException(status_code=409, detail=message) from exc
    return get_record_by_uid(db, payload.household_uid, user)


def update_record(
    db: Session,
    record: Distribution,
    payload: RecordUpdate,
    user: User,
    request=None,
) -> Distribution:
    if record.row_version != payload.expected_version:
        raise HTTPException(
            status_code=409,
            detail="This record changed after you opened it. Reload before editing.",
        )
    if (
        payload.household_uid or payload.serial_number or payload.distribution_point_id
    ) and not has_permission(user.role, Permission.RECORD_CHANGE_IDENTIFIERS):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only a data manager or administrator may change identifiers or distribution point"
            ),
        )

    before = record_snapshot(record)
    changes = payload.model_dump(exclude_unset=True, exclude={"expected_version", "reason"})
    household_fields = {
        "household_head_name",
        "family_name",
        "household_size",
        "phone_number",
        "additional_contact",
        "subcounty",
        "parish",
        "village",
    }
    distribution_fields = {
        "distributed_on",
        "receiver_type",
        "receiver_name",
        "receiver_relationship",
        "ambassador_name",
    }
    for field, value in changes.items():
        if field in household_fields:
            setattr(record.household, field, value)
        elif field == "household_uid":
            record.household.household_uid = value
            record.household.household_uid_norm = normalize_identifier(value)
        elif field == "serial_number":
            record.stove.serial_number = value
            record.stove.serial_number_norm = normalize_identifier(value)
        elif field == "stove_size":
            record.stove.stove_size = value
        elif field == "distribution_point_id":
            point = db.get(DistributionPoint, value)
            if not point or not point.active:
                raise HTTPException(status_code=400, detail="Select an active distribution point")
            record.distribution_point = point
        elif field in distribution_fields:
            setattr(record, field, value)

    record.row_version += 1
    record.household.row_version += 1
    record.stove.row_version += 1
    try:
        db.flush()
        audit_event(
            db,
            actor=user,
            action="record.updated",
            entity_type="distribution",
            entity_id=record.id,
            before=before,
            after=record_snapshot(record),
            reason=payload.reason,
            request=request,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        detail = "Household ID or stove serial number already exists"
        raise HTTPException(status_code=409, detail=detail) from exc
    return get_record_by_uid(db, record.household.household_uid, user)


def record_to_schema(record: Distribution) -> RecordOut:
    return RecordOut(
        id=record.id,
        household=HouseholdOut.model_validate(record.household),
        stove=StoveOut.model_validate(record.stove),
        distribution_point=DistributionPointOut.model_validate(record.distribution_point),
        distributed_on=record.distributed_on,
        receiver_type=record.receiver_type,
        receiver_name=record.receiver_name,
        receiver_relationship=record.receiver_relationship,
        carbon_waiver_accepted=record.carbon_waiver_accepted,
        conditions_accepted=record.conditions_accepted,
        ambassador_name=record.ambassador_name,
        verification_code=record.verification_code,
        signature_status=record.signature_status,
        row_version=record.row_version,
        signature_evidence=[
            SignatureEvidenceOut.model_validate(item)
            for item in sorted(
                record.signature_evidence, key=lambda item: item.created_at, reverse=True
            )
        ],
    )
