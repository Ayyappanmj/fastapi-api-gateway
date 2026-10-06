"""
/admin routes.

Read-only, paginated views over users, request_logs, and
blocked_requests for the admin dashboard. Folded in alongside
Analytics (Phase 8) since both are admin-only, read-only views over
the same underlying data this phase introduced aggregation for.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.blocked_request import BlockedRequest
from app.models.request_log import RequestLog
from app.models.user import User, UserRole
from app.schemas.admin import BlockedRequestOut, RequestLogOut
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
from app.utils.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


def _paginate(query, page: int, page_size: int, order_by):
    total = query.count()
    items = query.order_by(order_by).offset((page - 1) * page_size).limit(page_size).all()
    return total, items


@router.get("/users", response_model=PaginatedResponse[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> PaginatedResponse:
    total, items = _paginate(db.query(User), page, page_size, User.created_at.desc())
    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/logs", response_model=PaginatedResponse[RequestLogOut])
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    endpoint: str | None = Query(None, description="Filter to an exact endpoint path"),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> PaginatedResponse:
    query = db.query(RequestLog)
    if endpoint:
        query = query.filter(RequestLog.endpoint == endpoint)
    total, items = _paginate(query, page, page_size, RequestLog.timestamp.desc())
    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/blocked", response_model=PaginatedResponse[BlockedRequestOut])
def list_blocked(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN)),
) -> PaginatedResponse:
    total, items = _paginate(db.query(BlockedRequest), page, page_size, BlockedRequest.timestamp.desc())
    return PaginatedResponse(page=page, page_size=page_size, total=total, items=items)
