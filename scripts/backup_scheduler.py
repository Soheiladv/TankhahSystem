#!/usr/bin/env python
"""
اسکریپت اجرای پشتیبان‌گیری‌های زمان‌بندی شده
این اسکریپت باید توسط cron اجرا شود

مثال cron:
# هر 5 دقیقه یکبار بررسی کن
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر ساعت یکبار بررسی کن
0 * * * * /path/to/python /path/to/scripts/backup_scheduler.py
"""

import os
import sys
import django
import argparse
import logging
from pathlib import Path
from datetime import datetime

# اضافه کردن مسیر scripts به Python path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from config import (
    get_project_root, get_logs_dir, ensure_logs_dir, get_django_settings,
    get_log_config, get_backup_config, get_notification_config, get_cron_config
)

def setup_django():
    """تنظیم Django environment"""
    project_root = get_project_root()
    
    # اضافه کردن مسیر پروژه به Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # تنظیم Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', get_django_settings())
    django.setup()

def setup_logging(log_level=None, log_file=None):
    """تنظیم logging"""
    # دریافت تنظیمات از فایل config
    log_config = get_log_config()
    
    # ایجاد پوشه logs در صورت عدم وجود
    ensure_logs_dir()
    
    # تنظیم log level
    if not log_level:
        log_level = log_config['level']
    
    # تنظیم log file
    if not log_file:
        log_file = log_config['file']
    
    # تنظیم logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_config['format'],
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """تابع اصلی اجرای اسکریپت"""
    parser = argparse.ArgumentParser(description='اجرای پشتیبان‌گیری‌های زمان‌بندی شده')
    parser.add_argument('--schedule-id', type=int, help='اجرای اسکچول خاص')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='سطح لاگ')
    parser.add_argument('--log-file', help='مسیر فایل لاگ')
    parser.add_argument('--dry-run', action='store_true', help='اجرای تستی بدون انجام عملیات')
    
    args = parser.parse_args()
    
    # تنظیم Django
    setup_django()
    
    # تنظیم logging
    logger = setup_logging(args.log_level, args.log_file)
    
    try:
        from notificationApp.utils import check_and_execute_scheduled_backups, execute_scheduled_backup
        
        if args.dry_run:
            logger.info("اجرای تستی - هیچ عملیاتی انجام نخواهد شد")
            return
        
        if args.schedule_id:
            # اجرای اسکچول خاص
            logger.info(f"اجرای پشتیبان‌گیری برای اسکچول {args.schedule_id}...")
            success = execute_scheduled_backup(args.schedule_id)
            if success:
                logger.info(f"پشتیبان‌گیری اسکچول {args.schedule_id} با موفقیت تکمیل شد")
            else:
                logger.error(f"پشتیبان‌گیری اسکچول {args.schedule_id} ناموفق بود")
                sys.exit(1)
        else:
            # بررسی و اجرای همه اسکچول‌ها
            logger.info("شروع بررسی پشتیبان‌گیری‌های زمان‌بندی شده...")
            check_and_execute_scheduled_backups()
            logger.info("بررسی پشتیبان‌گیری‌ها تکمیل شد")
            
    except Exception as e:
        logger.error(f"خطا در اجرای اسکریپت: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
