#!/bin/sh
set -e

echo "Applying database migrations..."

# docker-compose's `depends_on: condition: service_healthy` already waits
# for Postgres to accept connections, but "accepting connections" and
# "ready for a schema migration" aren't quite the same moment — so this
# retries a few times instead of failing the container on the first blip.
attempt=1
max_attempts=10
until alembic upgrade head; do
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "Migrations failed after $max_attempts attempts. Exiting."
        exit 1
    fi
    echo "Migration attempt $attempt failed, retrying in 3s..."
    attempt=$((attempt + 1))
    sleep 3
done

echo "Migrations applied. Starting server..."
exec "$@"
