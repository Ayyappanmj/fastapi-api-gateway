"""
Pydantic schemas for the /admin routes.
"""
from datetime import datetime

from pydantic import BaseModel


class RequestLogOut(BaseModel):
    id: str
    user_id: str | None
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int
    ip_address: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class BlockedRequestOut(BaseModel):
    id: str
    user_id: str | None
    endpoint: str
    ip_address: str
    reason: str
    timestamp: datetime

    model_config = {"from_attributes": True}
