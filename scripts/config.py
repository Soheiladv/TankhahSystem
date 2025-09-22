"""
فایل تنظیمات برای اسکریپت‌های پشتیبان‌گیری
"""

import os
from pathlib import Path

# مسیرهای پروژه
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
LOGS_DIR = PROJECT_ROOT / 'logs'

# تنظیمات Django
DJANGO_SETTINGS_MODULE = 'BudgetsSystem.settings'

# تنظیمات لاگ
LOG_CONFIG = {
    'level': os.getenv('BACKUP_LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': LOGS_DIR / 'backup_scheduler.log',
    'error_file': LOGS_DIR / 'backup_scheduler_error.log',
    'max_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# تنظیمات پشتیبان‌گیری
BACKUP_CONFIG = {
    'default_format': 'json',
    'default_database': 'both',
    'encryption_enabled': True,
    'compression_enabled': True,
    'retention_days': 30,
}

# تنظیمات اعلان
NOTIFICATION_CONFIG = {
    'email_enabled': True,
    'email_from': 'system@example.com',
    'webhook_enabled': False,
    'webhook_url': None,
}

# تنظیمات cron
CRON_CONFIG = {
    'check_interval_minutes': 5,
    'max_concurrent_backups': 3,
    'timeout_seconds': 3600,  # 1 hour
}

def get_project_root():
    """بازگردانی مسیر ریشه پروژه"""
    return PROJECT_ROOT

def get_logs_dir():
    """بازگردانی مسیر پوشه لاگ‌ها"""
    return LOGS_DIR

def ensure_logs_dir():
    """اطمینان از وجود پوشه لاگ‌ها"""
    LOGS_DIR.mkdir(exist_ok=True)
    return LOGS_DIR

def get_django_settings():
    """بازگردانی تنظیمات Django"""
    return DJANGO_SETTINGS_MODULE

def get_log_config():
    """بازگردانی تنظیمات لاگ"""
    return LOG_CONFIG.copy()

def get_backup_config():
    """بازگردانی تنظیمات پشتیبان‌گیری"""
    return BACKUP_CONFIG.copy()

def get_notification_config():
    """بازگردانی تنظیمات اعلان"""
    return NOTIFICATION_CONFIG.copy()

def get_cron_config():
    """بازگردانی تنظیمات cron"""
    return CRON_CONFIG.copy()
