import re
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from api.audit import audit_event, record_snapshot
from api.dependencies import DbSession, enforce_point_scope, require_permission
from api.models import Distribution, SignatureEvidence, SignatureStatus, User
from api.permissions import Permission
from api.schemas import RecordOut, SignatureReview
from api.services import get_record_by_uid, record_to_schema
from api.storage import EvidenceStorage

router = APIRouter(prefix="/signatures", tags=["signatures"])


@router.post("/{household_uid}", response_model=RecordOut, status_code=201)
async def capture_signature_evidence(
    household_uid: str,
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.SIGNATURE_CAPTURE))],
    evidence: UploadFile = File(...),
    beneficiary_name: str = Form(..., min_length=2, max_length=180),
    witness_name: str = Form(..., min_length=2, max_length=180),
    signed_at: datetime = Form(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    notes: str | None = Form(default=None, max_length=1000),
):
    record = get_record_by_uid(db, household_uid, user)
    stored = await EvidenceStorage().put(record.id, evidence)
    before = record_snapshot(record)
    item = SignatureEvidence(
        distribution_id=record.id,
        beneficiary_name=beneficiary_name.strip(),
        witness_name=witness_name.strip(),
        signed_at=signed_at,
        object_key=stored.object_key,
        original_filename=stored.original_filename,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
        captured_by_user_id=user.id,
    )
    db.add(item)
    record.signature_status = SignatureStatus.CAPTURED
    record.row_version += 1
    db.flush()
    audit_event(
        db,
        actor=user,
        action="signature.captured",
        entity_type="distribution",
        entity_id=record.id,
        before=before,
        after={**record_snapshot(record), "evidence_sha256": stored.sha256},
        request=request,
    )
    db.commit()
    return record_to_schema(get_record_by_uid(db, household_uid, user))


@router.post("/evidence/{evidence_id}/review", response_model=RecordOut)
def review_signature_evidence(
    evidence_id: str,
    payload: SignatureReview,
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.SIGNATURE_VERIFY))],
):
    evidence = db.scalar(
        select(SignatureEvidence)
        .options(
            joinedload(SignatureEvidence.distribution).joinedload(Distribution.household),
            joinedload(SignatureEvidence.distribution).joinedload(Distribution.stove),
            joinedload(SignatureEvidence.distribution).joinedload(Distribution.distribution_point),
        )
        .where(SignatureEvidence.id == evidence_id)
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Signature evidence was not found")
    record = evidence.distribution
    enforce_point_scope(user, record.distribution_point_id)
    before = record_snapshot(record)
    if payload.approve:
        evidence.verified_by_user_id = user.id
        evidence.verified_at = datetime.now(UTC)
        evidence.rejected_reason = None
        record.signature_status = SignatureStatus.VERIFIED
        action = "signature.verified"
    else:
        evidence.verified_by_user_id = None
        evidence.verified_at = None
        evidence.rejected_reason = payload.reason
        record.signature_status = SignatureStatus.REJECTED
        action = "signature.rejected"
    record.row_version += 1
    audit_event(
        db,
        actor=user,
        action=action,
        entity_type="distribution",
        entity_id=record.id,
        before=before,
        after=record_snapshot(record),
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return record_to_schema(get_record_by_uid(db, record.household.household_uid, user))


@router.get("/evidence/{evidence_id}/file")
def download_evidence(
    evidence_id: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_VIEW))],
):
    evidence = db.scalar(
        select(SignatureEvidence)
        .options(joinedload(SignatureEvidence.distribution))
        .where(SignatureEvidence.id == evidence_id)
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Signature evidence was not found")
    enforce_point_scope(user, evidence.distribution.distribution_point_id)
    raw = EvidenceStorage().get(evidence.object_key)
    safe_filename = re.sub(r"[^A-Za-z0-9._-]+", "_", evidence.original_filename)
    return Response(
        content=raw,
        media_type=evidence.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
