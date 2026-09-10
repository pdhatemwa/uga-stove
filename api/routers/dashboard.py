from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select

from api.dependencies import DbSession, require_permission
from api.models import Distribution, DistributionPoint, SignatureStatus, Stove, User
from api.permissions import Permission
from api.schemas import DashboardPointRow, DashboardSummaryOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(
    db: DbSession,
    user: Annotated[User, Depends(require_permission(Permission.DASHBOARD_VIEW))],
):
    scope = []
    if user.distribution_point_id:
        scope.append(Distribution.distribution_point_id == user.distribution_point_id)

    totals = db.execute(
        select(
            func.count(Distribution.id),
            func.count(func.distinct(Distribution.household_id)),
            func.count(func.distinct(Distribution.stove_id)),
            func.sum(case((Distribution.signature_status == SignatureStatus.CAPTURED, 1), else_=0)),
            func.sum(case((Distribution.signature_status == SignatureStatus.VERIFIED, 1), else_=0)),
            func.sum(case((Distribution.signature_status == SignatureStatus.UNSIGNED, 1), else_=0)),
        ).where(*scope)
    ).one()

    size_rows = db.execute(
        select(func.lower(Stove.stove_size), func.count(Stove.id))
        .join(Distribution, Distribution.stove_id == Stove.id)
        .where(*scope)
        .group_by(func.lower(Stove.stove_size))
    ).all()
    sizes = {str(name): count for name, count in size_rows}

    point_rows = db.execute(
        select(
            DistributionPoint.name,
            func.count(Distribution.id),
            func.sum(case((Distribution.signature_status == SignatureStatus.CAPTURED, 1), else_=0)),
            func.sum(case((Distribution.signature_status == SignatureStatus.VERIFIED, 1), else_=0)),
        )
        .join(Distribution, Distribution.distribution_point_id == DistributionPoint.id)
        .where(*scope)
        .group_by(DistributionPoint.id, DistributionPoint.name)
        .order_by(DistributionPoint.name)
    ).all()

    date_rows = db.execute(
        select(Distribution.distributed_on, func.count(Distribution.id))
        .where(*scope)
        .group_by(Distribution.distributed_on)
        .order_by(Distribution.distributed_on)
    ).all()

    return DashboardSummaryOut(
        total_distributions=totals[0] or 0,
        unique_households=totals[1] or 0,
        unique_stoves=totals[2] or 0,
        captured_signatures=totals[3] or 0,
        verified_signatures=totals[4] or 0,
        unsigned_records=totals[5] or 0,
        large_stoves=sizes.get("large", 0),
        medium_stoves=sizes.get("medium", 0),
        small_stoves=sizes.get("small", 0),
        by_distribution_point=[
            DashboardPointRow(
                distribution_point=name,
                total=total,
                signed=captured or 0,
                verified=verified or 0,
            )
            for name, total, captured, verified in point_rows
        ],
        by_date=[{"date": day.isoformat(), "total": total} for day, total in date_rows],
    )
