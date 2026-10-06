"""
/analytics routes.

Every route here is admin-only (require_role from Phase 4) — these
power the monitoring dashboard, not something a regular API consumer
needs to see about other users' traffic.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import UserRole
from app.schemas.analytics import EndpointsResponse, OverviewResponse, TrafficResponse
from app.services import analytics_service
from app.utils.dependencies import require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewResponse)
def overview(
    hours: int = Query(24, ge=1, le=720, description="Look-back window in hours"),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> dict:
    return analytics_service.get_overview(db, hours=hours)


@router.get("/traffic", response_model=TrafficResponse)
def traffic(
    granularity: str = Query("hourly", pattern="^(hourly|daily)$"),
    hours: int = Query(24, ge=1, le=168, description="Used when granularity=hourly"),
    days: int = Query(7, ge=1, le=90, description="Used when granularity=daily"),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> dict:
    try:
        return analytics_service.get_traffic(db, granularity=granularity, hours=hours, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/endpoints", response_model=EndpointsResponse)
def endpoints(
    hours: int = Query(168, ge=1, le=720, description="Look-back window in hours"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> dict:
    return analytics_service.get_endpoint_breakdown(db, hours=hours, limit=limit)
