#!/usr/bin/env python
"""
ایجاد فایل .env کامل
این اسکریپت فایل .env کامل با تمام تنظیمات را ایجاد می‌کند
"""

import os
from datetime import datetime

def create_complete_env_file():
    """ایجاد فایل .env کامل"""
    
    print("📝 ایجاد فایل .env کامل")
    print("=" * 40)
    
    env_content = """# تنظیمات اصلی Django
SECRET_KEY=django-insecure-default-key-for-dev-only
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
CSRF_TRUSTED_ORIGINS=

# تنظیمات دیتابیس MySQL
DATABASE_DEFAULT_NAME=tankhasystem
DATABASE_DEFAULT_USER=root
DATABASE_DEFAULT_PASSWORD=S@123456@1234
DATABASE_DEFAULT_HOST=127.0.0.1
DATABASE_DEFAULT_PORT=3306

# تنظیمات دیتابیس لاگ
DATABASE_LOGS_NAME=tankhah_logs_db
DATABASE_LOGS_USER=root
DATABASE_LOGS_PASSWORD=S@123456@1234
DATABASE_LOGS_HOST=127.0.0.1
DATABASE_LOGS_PORT=3306

# تنظیمات ایمیل
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# تنظیمات Redis (برای cache و channels)
REDIS_URL=redis://127.0.0.1:6379/0

# تنظیمات فایل‌های استاتیک
STATIC_URL=/static/
STATIC_ROOT=staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=media

# تنظیمات امنیتی
SECURE_SSL_REDIRECT=False
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=DENY

# تنظیمات لاگ
LOG_LEVEL=INFO
LOG_FILE=logs/django.log

# تنظیمات backup
BACKUP_ENABLED=True
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=30

# تنظیمات USB Dongle Validation
USB_DONGLE_VALIDATION_ENABLED=false
USB_DONGLE_CACHE_TIMEOUT=300
USB_DONGLE_NOTIFICATIONS_ENABLED=true
USB_DONGLE_DEBUG_MODE=false

# تنظیمات اعلان‌ها
NOTIFICATION_ENABLED=true
NOTIFICATION_CHANNELS=in_app,email
NOTIFICATION_RETENTION_DAYS=30

# تنظیمات workflow
WORKFLOW_ENABLED=true
WORKFLOW_AUTO_APPROVE=false
WORKFLOW_NOTIFICATION_ENABLED=true

# تنظیمات گزارش‌گیری
REPORT_ENABLED=true
REPORT_CACHE_TIMEOUT=600
REPORT_MAX_RECORDS=10000

# تنظیمات version tracking
VERSION_TRACKING_ENABLED=true
VERSION_AUTO_BACKUP=true
VERSION_RETENTION_COUNT=10

# تنظیمات فاکتور
FACTOR_ENABLED=true
FACTOR_AUTO_NUMBERING=true
FACTOR_MAX_ITEMS=50
FACTOR_MAX_AMOUNT=1000000000

# تنظیمات تنخواه
TANKHAH_ENABLED=true
TANKHAH_AUTO_APPROVE=false
TANKHAH_MAX_AMOUNT=5000000000

# تنظیمات بودجه
BUDGET_ENABLED=true
BUDGET_AUTO_CALCULATION=true
BUDGET_WARNING_THRESHOLD=0.8

# تنظیمات کاربران
USER_ENABLED=true
USER_AUTO_ACTIVATION=false
USER_PASSWORD_EXPIRY_DAYS=90

# تنظیمات سازمان
ORGANIZATION_ENABLED=true
ORGANIZATION_AUTO_ASSIGNMENT=false

# تنظیمات پروژه
PROJECT_ENABLED=true
PROJECT_AUTO_BUDGET_ALLOCATION=false

# تنظیمات پرداخت
PAYMENT_ENABLED=true
PAYMENT_AUTO_APPROVE=false
PAYMENT_MAX_AMOUNT=1000000000

# تنظیمات گزارش‌گیری پیشرفته
ADVANCED_REPORTING=true
REPORT_CACHE_ENABLED=true
REPORT_EXPORT_FORMATS=pdf,excel,csv

# تنظیمات امنیتی پیشرفته
ADVANCED_SECURITY=true
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900

# تنظیمات عملکرد
PERFORMANCE_OPTIMIZATION=true
QUERY_CACHE_ENABLED=true
PAGINATION_SIZE=20
BULK_OPERATION_LIMIT=1000

# تنظیمات توسعه
DEVELOPMENT_MODE=true
DEBUG_TOOLBAR=false
PROFILING_ENABLED=false
TEST_DATA_ENABLED=false
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ فایل .env کامل ایجاد شد")
        
        # نمایش آمار
        lines = env_content.count('\n')
        print(f"📊 تعداد خطوط: {lines}")
        print(f"📊 تعداد تنظیمات: {env_content.count('=')}")
        
        print(f"\n📋 دسته‌بندی تنظیمات:")
        categories = [
            ('Django', 'SECRET_KEY,DEBUG,ALLOWED_HOSTS'),
            ('Database', 'DATABASE_'),
            ('Email', 'EMAIL_'),
            ('Redis', 'REDIS_'),
            ('Static/Media', 'STATIC_,MEDIA_'),
            ('Security', 'SECURE_,X_FRAME_'),
            ('Logging', 'LOG_'),
            ('Backup', 'BACKUP_'),
            ('USB Dongle', 'USB_DONGLE_'),
            ('Notifications', 'NOTIFICATION_'),
            ('Workflow', 'WORKFLOW_'),
            ('Reports', 'REPORT_'),
            ('Version Tracking', 'VERSION_'),
            ('Factor', 'FACTOR_'),
            ('Tankhah', 'TANKHAH_'),
            ('Budget', 'BUDGET_'),
            ('Users', 'USER_'),
            ('Organization', 'ORGANIZATION_'),
            ('Project', 'PROJECT_'),
            ('Payment', 'PAYMENT_'),
            ('Advanced', 'ADVANCED_'),
            ('Performance', 'PERFORMANCE_'),
            ('Development', 'DEVELOPMENT_')
        ]
        
        for category, pattern in categories:
            count = env_content.count(pattern)
            if count > 0:
                print(f"   {category}: {count} تنظیم")
        
    except Exception as e:
        print(f"❌ خطا در ایجاد فایل .env: {e}")

def show_env_usage_guide():
    """نمایش راهنمای استفاده از .env"""
    
    print(f"\n📖 راهنمای استفاده از .env:")
    print("=" * 40)
    
    print("🔧 نحوه استفاده:")
    print("   1. فایل .env را ویرایش کنید")
    print("   2. مقادیر مورد نظر را تغییر دهید")
    print("   3. Django را restart کنید")
    
    print(f"\n⚠️ نکات مهم:")
    print("   - فایل .env را در git commit نکنید")
    print("   - از مقادیر پیش‌فرض برای production استفاده نکنید")
    print("   - رمزهای عبور را محرمانه نگه دارید")
    
    print(f"\n🔒 تنظیمات امنیتی:")
    print("   - SECRET_KEY: کلید مخفی Django")
    print("   - DEBUG: حالت دیباگ (فقط برای development)")
    print("   - SECURE_SSL_REDIRECT: اجباری کردن HTTPS")
    
    print(f"\n🗄️ تنظیمات دیتابیس:")
    print("   - DATABASE_DEFAULT_*: دیتابیس اصلی")
    print("   - DATABASE_LOGS_*: دیتابیس لاگ‌ها")
    
    print(f"\n📧 تنظیمات ایمیل:")
    print("   - EMAIL_HOST: سرور SMTP")
    print("   - EMAIL_HOST_USER: نام کاربری ایمیل")
    print("   - EMAIL_HOST_PASSWORD: رمز عبور ایمیل")

if __name__ == "__main__":
    create_complete_env_file()
    show_env_usage_guide()
