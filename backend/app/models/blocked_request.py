"""
blocked_requests table.

Logged whenever the rate limiter rejects a request with 429 (Phase 6).
Kept separate from request_logs (rather than just filtering
status_code=429 there) so the admin "blocked requests" view and abuse
detection queries stay cheap even as request_logs grows large.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BlockedRequest(Base):
    __tablename__ = "blocked_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="rate_limit_exceeded")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
