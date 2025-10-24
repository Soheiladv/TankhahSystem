#!/bin/bash
# Restore script for Budgets System

set -e

BACKUP_DIR="/backups"

if [ -z "$1" ]; then
    echo "❌ Please provide backup file name"
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_DIR/$BACKUP_FILE"
    exit 1
fi

echo "🔄 Starting restore process..."
echo "📁 Backup file: $BACKUP_FILE"

# Stop application to prevent data corruption
echo "⏹️  Stopping application..."
docker-compose stop web celery celery-beat

# Restore database
echo "🗄️  Restoring database..."
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip -c $BACKUP_DIR/$BACKUP_FILE | docker-compose exec -T db psql -U ${DB_USER:-budgets_user} -d ${DB_NAME:-budgets_db}
else
    docker-compose exec -T db psql -U ${DB_USER:-budgets_user} -d ${DB_NAME:-budgets_db} < $BACKUP_DIR/$BACKUP_FILE
fi

# Start application
echo "🚀 Starting application..."
docker-compose start web celery celery-beat

echo "✅ Restore completed successfully!"
