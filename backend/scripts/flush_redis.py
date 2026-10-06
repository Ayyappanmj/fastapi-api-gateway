"""Flush the configured Redis database after explicit confirmation.

Run from the backend directory with ``python scripts/flush_redis.py``.
"""
import argparse

from app.config import get_settings
from app.services.redis_client import get_redis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="allow flushing Redis when ENVIRONMENT is production",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.environment.lower() == "production" and not args.allow_production:
        parser.error("refusing to flush production Redis without --allow-production")

    print(f"Target environment: {settings.environment}")
    print("This permanently deletes every key in the configured Redis database.")
    if input('Type "FLUSHDB" to continue: ') != "FLUSHDB":
        print("Aborted; no keys were deleted.")
        return 1

    client = get_redis()
    try:
        client.flushdb()
    finally:
        client.close()

    print("Redis database flushed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())