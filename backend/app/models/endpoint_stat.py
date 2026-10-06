"""
endpoint_stats table.

Daily pre-aggregated rollup per (endpoint, method). The analytics
dashboard reads from here for "top endpoints" / "slow endpoints"
instead of scanning all of request_logs on every page load. A
scheduled job (or an on-write increment in the gateway service)
upserts these rows — implemented in Phase 8.
"""
import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EndpointStat(Base):
    __tablename__ = "endpoint_stats"
    __table_args__ = (
        UniqueConstraint("endpoint", "method", "date", name="uq_endpoint_stats_endpoint_method_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
