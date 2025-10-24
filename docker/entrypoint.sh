#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Create necessary directories
mkdir -p /app/logs
mkdir -p /app/staticfiles
mkdir -p /app/mediafiles

# Set proper permissions
chown -R django:django /app/logs
chown -R django:django /app/staticfiles
chown -R django:django /app/mediafiles

# Execute the main command
exec "$@"
