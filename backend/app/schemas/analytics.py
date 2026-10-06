"""
Pydantic schemas for the /analytics routes.
"""
from pydantic import BaseModel


class OverviewResponse(BaseModel):
    window_hours: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    blocked_requests: int
    active_users: int
    avg_response_time_ms: float
    requests_per_minute: float
    error_rate_percent: float


class TrafficPoint(BaseModel):
    bucket: str
    request_count: int


class TrafficResponse(BaseModel):
    granularity: str
    points: list[TrafficPoint]


class EndpointBreakdown(BaseModel):
    endpoint: str
    method: str
    total_requests: int
    total_errors: int
    avg_response_time_ms: float
    error_rate_percent: float


class UserActivity(BaseModel):
    user_id: str
    email: str
    request_count: int


class EndpointsResponse(BaseModel):
    top_endpoints: list[EndpointBreakdown]
    slow_endpoints: list[EndpointBreakdown]
    most_active_users: list[UserActivity]
