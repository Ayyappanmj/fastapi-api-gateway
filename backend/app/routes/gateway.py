"""
/gateway routes.

POST /gateway/request is authenticated AND rate-limited (via
rate_limited, Phase 6's token bucket dependency). GET /gateway/status
only requires authentication — status checks shouldn't themselves be
throttled.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.middleware.rate_limit import rate_limited
from app.models.user import User
from app.schemas.gateway import (
    GatewayRequestPayload,
    GatewayResponse,
    GatewayResponseMeta,
    GatewayStatusResponse,
)
from app.services import gateway_service
from app.services.gateway_service import GatewayError
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/request", response_model=GatewayResponse)
def gateway_request(
    payload: GatewayRequestPayload, current_user: User = Depends(rate_limited)
) -> GatewayResponse:
    try:
        result = gateway_service.route_request(
            target_service=payload.target_service,
            method=payload.method,
            path=payload.path,
            body=payload.body,
        )
    except GatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return GatewayResponse(
        meta=GatewayResponseMeta(
            service=result["service"],
            path=result["path"],
            method=result["method"],
            status_code=200,
            response_time_ms=result["response_time_ms"],
        ),
        data=result["data"],
    )


@router.get("/status", response_model=GatewayStatusResponse)
def gateway_status(current_user: User = Depends(get_current_user)) -> GatewayStatusResponse:
    return GatewayStatusResponse(
        gateway="operational",
        registered_services=gateway_service.list_registered_services(),
        requested_by=current_user.email,
    )
