#!/bin/bash
set -e

echo "Starting database initialization..."

# خواندن پسورد root از فایل secret
ROOT_PASSWORD=$(cat /run/secrets/db_password 2>/dev/null || echo "BudgetsDB2024!SecurePass#2486")
USER_PASSWORD="$ROOT_PASSWORD"

# صبر کردن تا MySQL آماده شود
until mysqladmin ping -h localhost -uroot -p"$ROOT_PASSWORD" --silent; do
  echo "Waiting for MySQL to be ready..."
  sleep 2
done

echo "MySQL is ready. Creating database and user..."

# ایجاد دیتابیس و کاربر
mysql -uroot -p"$ROOT_PASSWORD" <<EOF
-- ایجاد دیتابیس
CREATE DATABASE IF NOT EXISTS budgets_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- حذف کاربر قبلی در صورت وجود
DROP USER IF EXISTS 'budgets_user'@'%';

-- ایجاد کاربر جدید
CREATE USER 'budgets_user'@'%' IDENTIFIED BY '$USER_PASSWORD';

-- اعطای دسترسی
GRANT ALL PRIVILEGES ON budgets_db.* TO 'budgets_user'@'%';
FLUSH PRIVILEGES;

-- نمایش نتیجه
SELECT 'Database and user created successfully!' AS status;
EOF

echo "Database initialization completed!"

