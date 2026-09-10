from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from api.dependencies import DbSession, require_permission
from api.models import DistributionPoint, User
from api.permissions import Permission
from api.schemas import DistributionPointOut

router = APIRouter(prefix="/distribution-points", tags=["distribution points"])


@router.get("", response_model=list[DistributionPointOut])
def list_distribution_points(
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.RECORD_CREATE))],
):
    return db.scalars(
        select(DistributionPoint)
        .where(DistributionPoint.active.is_(True))
        .order_by(DistributionPoint.name)
    ).all()
