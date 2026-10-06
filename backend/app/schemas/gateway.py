"""
Pydantic schemas for the /gateway routes.
"""
from pydantic import BaseModel, field_validator

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


class GatewayRequestPayload(BaseModel):
    target_service: str
    method: str = "GET"
    path: str = "/"
    body: dict | None = None

    @field_validator("method")
    @classmethod
    def method_must_be_supported(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_METHODS:
            raise ValueError(f"Unsupported HTTP method '{value}'. Allowed: {sorted(ALLOWED_METHODS)}")
        return upper

    @field_validator("path")
    @classmethod
    def path_must_start_with_slash(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        return value


class GatewayResponseMeta(BaseModel):
    service: str
    path: str
    method: str
    status_code: int
    response_time_ms: float


class GatewayResponse(BaseModel):
    success: bool = True
    meta: GatewayResponseMeta
    data: dict


class GatewayStatusResponse(BaseModel):
    gateway: str
    registered_services: list[str]
    requested_by: str
