#!/bin/bash
# Backup script for Budgets System

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="budgets_backup_${DATE}.sql"

echo "🔄 Starting backup process..."

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Database backup
echo "🗄️  Backing up database..."
docker-compose exec -T db pg_dump -U ${DB_USER:-budgets_user} -d ${DB_NAME:-budgets_db} > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
echo "📦 Compressing backup..."
gzip $BACKUP_DIR/$BACKUP_FILE

# Remove old backups (keep last 30 days)
echo "🧹 Cleaning old backups..."
find $BACKUP_DIR -name "budgets_backup_*.sql.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_FILE.gz"

# Optional: Upload to cloud storage
if [ "$BACKUP_STORAGE_TYPE" = "s3" ]; then
    echo "☁️  Uploading to S3..."
    aws s3 cp $BACKUP_DIR/$BACKUP_FILE.gz s3://$AWS_STORAGE_BUCKET_NAME/backups/
    echo "✅ Backup uploaded to S3"
fi
