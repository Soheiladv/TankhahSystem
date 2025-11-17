#!/bin/bash
set -e

# Load secrets from Docker secrets files if available
load_secret() {
  local var_name="$1"
  local file_path="$2"

  if [ -n "$file_path" ] && [ -f "$file_path" ]; then
    export "$var_name"="$(cat "$file_path" | tr -d '\r')"
  fi
}

load_secret "SECRET_KEY" "${SECRET_KEY_FILE:-${SECRET_KEY_FILE_PATH:-}}"
load_secret "DB_PASSWORD" "${DB_PASSWORD_FILE:-${DB_PASSWORD_FILE_PATH:-}}"
load_secret "REDIS_PASSWORD" "${REDIS_PASSWORD_FILE:-${REDIS_PASSWORD_FILE_PATH:-}}"

if [ -n "$REDIS_PASSWORD" ] && [ -z "$REDIS_URL" ]; then
  REDIS_HOST_ENV="${REDIS_HOST:-redis}"
  REDIS_PORT_ENV="${REDIS_PORT:-6379}"
  export REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST_ENV}:${REDIS_PORT_ENV}/0"
fi

# Wait for database to be ready
echo "Waiting for database..."
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
    echo "Database is ready!"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Waiting for database at $DB_HOST:$DB_PORT... (attempt $RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "ERROR: Could not connect to database at $DB_HOST:$DB_PORT after $MAX_RETRIES attempts"
  echo "Please check:"
  echo "  1. Is the database service running? (docker-compose ps)"
  echo "  2. Is the network configured correctly? (docker network ls)"
  echo "  3. Are you running this container with docker-compose up?"
  exit 1
fi

# Wait for Redis to be ready
echo "Waiting for Redis..."
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
    echo "Redis is ready!"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT... (attempt $RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "WARNING: Could not connect to Redis at $REDIS_HOST:$REDIS_PORT after $MAX_RETRIES attempts"
  echo "Continuing anyway, but Redis features may not work..."
fi

# Create necessary directories if they don't exist
mkdir -p /app/logs /app/staticfiles /app/mediafiles

# Run migrations (unless explicitly skipped)
if [ "${SKIP_ENTRYPOINT_MIGRATIONS:-0}" = "1" ]; then
  echo "Skipping automatic migrations (SKIP_ENTRYPOINT_MIGRATIONS=1)..."
else
  echo "Running database migrations..."
  python manage.py migrate --noinput || {
      echo "Warning: Migrations failed, continuing anyway..."
  }

  echo "Collecting static files..."
  python manage.py collectstatic --noinput || {
      echo "Warning: Collectstatic failed, continuing anyway..."
  }
fi

# Create superuser if it doesn't exist (only in development)
if [ "${DEBUG:-False}" = "True" ] && [ -z "${DJANGO_SUPERUSER_PASSWORD}" ]; then
    echo "Checking for superuser..."
    python manage.py shell << 'EOF' || true
from django.contrib.auth import get_user_model
import os
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    User.objects.create_superuser('admin', 'admin@example.com', password)
    print('Superuser created: admin')
else:
    print('Superuser already exists')
EOF
fi

# Execute the main command
# Note: The container should run as django user (set USER django in Dockerfile)
# If running as root, you may want to switch users here for security
echo "Starting application as user $(whoami)..."
exec "$@"
