"""
Analytics aggregation.

Everything here reads directly from `request_logs` / `blocked_requests`
(populated by Phase 7's logging middleware) rather than from the
`endpoint_stats` rollup table. That table exists in the schema (Phase
3) as the documented place a *scheduled job* would pre-aggregate daily
summaries for a high-traffic production system — wiring that job is
future work, noted here rather than faked, since doing it correctly
needs a real scheduler (cron / Celery beat) this project doesn't set
up. At portfolio scale, direct aggregation on every request is simple,
correct, and fast enough.

All grouping/bucketing is done with SQLAlchemy's cross-dialect
functions (func.count, func.avg, case()) rather than Postgres-specific
SQL, and hour/day bucketing is done in Python — so the exact same code
runs against SQLite in tests and Postgres in production.
"""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.blocked_request import BlockedRequest
from app.models.request_log import RequestLog
from app.models.user import User


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_overview(db: Session, hours: int = 24) -> dict:
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    base_q = db.query(RequestLog).filter(RequestLog.timestamp >= window_start)

    total_requests = base_q.count()
    successful_requests = base_q.filter(RequestLog.status_code < 400).count()
    failed_requests = total_requests - successful_requests

    blocked_requests = (
        db.query(BlockedRequest).filter(BlockedRequest.timestamp >= window_start).count()
    )
    active_users = (
        db.query(RequestLog.user_id)
        .filter(RequestLog.timestamp >= window_start, RequestLog.user_id.isnot(None))
        .distinct()
        .count()
    )
    avg_response_time_ms = base_q.with_entities(func.avg(RequestLog.response_time_ms)).scalar()

    window_minutes = max(hours * 60, 1)
    requests_per_minute = total_requests / window_minutes
    error_rate_percent = (failed_requests / total_requests * 100) if total_requests else 0.0

    return {
        "window_hours": hours,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "blocked_requests": blocked_requests,
        "active_users": active_users,
        "avg_response_time_ms": round(float(avg_response_time_ms or 0.0), 2),
        "requests_per_minute": round(requests_per_minute, 2),
        "error_rate_percent": round(error_rate_percent, 2),
    }


def get_traffic(db: Session, granularity: str = "hourly", hours: int = 24, days: int = 7) -> dict:
    if granularity not in ("hourly", "daily"):
        raise ValueError("granularity must be 'hourly' or 'daily'")

    if granularity == "hourly":
        window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
        bucket_format, bucket_count, bucket_delta = "%Y-%m-%d %H:00", hours, timedelta(hours=1)
    else:
        window_start = datetime.now(timezone.utc) - timedelta(days=days)
        bucket_format, bucket_count, bucket_delta = "%Y-%m-%d", days, timedelta(days=1)

    rows = db.query(RequestLog.timestamp).filter(RequestLog.timestamp >= window_start).all()

    counts: dict[str, int] = {}
    for (ts,) in rows:
        key = _as_utc(ts).strftime(bucket_format)
        counts[key] = counts.get(key, 0) + 1

    # Fill zero-count buckets so a chart built from this has no gaps.
    ordered: "OrderedDict[str, int]" = OrderedDict()
    cursor = datetime.now(timezone.utc) - bucket_delta * (bucket_count - 1)
    for _ in range(bucket_count):
        key = cursor.strftime(bucket_format)
        ordered[key] = counts.get(key, 0)
        cursor += bucket_delta

    return {
        "granularity": granularity,
        "points": [{"bucket": k, "request_count": v} for k, v in ordered.items()],
    }


def get_endpoint_breakdown(db: Session, hours: int = 168, limit: int = 10) -> dict:
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)

    rows = (
        db.query(
            RequestLog.endpoint,
            RequestLog.method,
            func.count(RequestLog.id).label("total_requests"),
            func.sum(case((RequestLog.status_code >= 400, 1), else_=0)).label("total_errors"),
            func.avg(RequestLog.response_time_ms).label("avg_response_time_ms"),
        )
        .filter(RequestLog.timestamp >= window_start)
        .group_by(RequestLog.endpoint, RequestLog.method)
        .all()
    )

    breakdown = []
    for endpoint, method, total_requests, total_errors, avg_ms in rows:
        total_errors = total_errors or 0
        avg_ms = float(avg_ms or 0.0)
        error_rate = (total_errors / total_requests * 100) if total_requests else 0.0
        breakdown.append(
            {
                "endpoint": endpoint,
                "method": method,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "avg_response_time_ms": round(avg_ms, 2),
                "error_rate_percent": round(error_rate, 2),
            }
        )

    top_endpoints = sorted(breakdown, key=lambda r: r["total_requests"], reverse=True)[:limit]
    slow_endpoints = sorted(breakdown, key=lambda r: r["avg_response_time_ms"], reverse=True)[:limit]

    user_rows = (
        db.query(User.id, User.email, func.count(RequestLog.id).label("request_count"))
        .join(RequestLog, RequestLog.user_id == User.id)
        .filter(RequestLog.timestamp >= window_start)
        .group_by(User.id, User.email)
        .order_by(func.count(RequestLog.id).desc())
        .limit(limit)
        .all()
    )
    most_active_users = [
        {"user_id": uid, "email": email, "request_count": count} for uid, email, count in user_rows
    ]

    return {
        "top_endpoints": top_endpoints,
        "slow_endpoints": slow_endpoints,
        "most_active_users": most_active_users,
    }
