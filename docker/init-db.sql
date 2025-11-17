-- ایجاد دیتابیس
CREATE DATABASE IF NOT EXISTS budgets_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ایجاد کاربر و اعطای دسترسی
CREATE USER IF NOT EXISTS 'budgets_user'@'%' IDENTIFIED BY 'BudgetsDB2024!SecurePass#2486';
GRANT ALL PRIVILEGES ON budgets_db.* TO 'budgets_user'@'%';
FLUSH PRIVILEGES;

