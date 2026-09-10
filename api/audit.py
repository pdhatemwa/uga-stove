from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from api.models import AuditLog, User


def audit_event(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    request: Request | None = None,
) -> None:
    request_id = getattr(request.state, "request_id", None) if request else None
    client_ip = request.client.host if request and request.client else None
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before,
            after_json=after,
            reason=reason,
            request_id=request_id,
            client_ip=client_ip,
        )
    )


def record_snapshot(distribution) -> dict[str, Any]:
    return {
        "household_uid": distribution.household.household_uid,
        "household_head_name": distribution.household.household_head_name,
        "household_size": distribution.household.household_size,
        "phone_number": distribution.household.phone_number,
        "subcounty": distribution.household.subcounty,
        "parish": distribution.household.parish,
        "village": distribution.household.village,
        "serial_number": distribution.stove.serial_number,
        "stove_size": distribution.stove.stove_size,
        "distribution_point_id": distribution.distribution_point_id,
        "distributed_on": distribution.distributed_on.isoformat(),
        "receiver_type": distribution.receiver_type,
        "receiver_name": distribution.receiver_name,
        "ambassador_name": distribution.ambassador_name,
        "signature_status": distribution.signature_status.value,
        "row_version": distribution.row_version,
    }
