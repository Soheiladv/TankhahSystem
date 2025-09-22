#!/usr/bin/env python
"""
اسکریپت پشتیبان‌گیری خودکار برای هر دو دیتابیس
"""
import os
import sys
import django
from datetime import datetime, timedelta
import logging

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.core.management import call_command
from django.conf import settings

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def backup_databases():
    """پشتیبان‌گیری از هر دو دیتابیس"""
    try:
        logger.info("شروع پشتیبان‌گیری خودکار...")
        
        # پشتیبان‌گیری از دیتابیس اصلی
        logger.info("پشتیبان‌گیری از دیتابیس اصلی...")
        call_command('dbbackup', '--compress')
        
        # پشتیبان‌گیری از دیتابیس لاگ
        logger.info("پشتیبان‌گیری از دیتابیس لاگ...")
        call_command('dbbackup', '--database=tankhah_logs_db', '--compress')
        
        # پاکسازی فایل‌های قدیمی
        logger.info("پاکسازی فایل‌های قدیمی...")
        call_command('dbbackup', '--cleanup')
        
        logger.info("پشتیبان‌گیری خودکار تکمیل شد")
        return True
        
    except Exception as e:
        logger.error(f"خطا در پشتیبان‌گیری: {str(e)}")
        return False

def check_backup_status():
    """بررسی وضعیت پشتیبان‌گیری"""
    backup_dir = settings.DBBACKUP_STORAGE_OPTIONS['location']
    
    if not os.path.exists(backup_dir):
        logger.warning("پوشه پشتیبان‌گیری وجود ندارد")
        return False
    
    # بررسی فایل‌های پشتیبان امروز
    today = datetime.now().strftime('%Y%m%d')
    backup_files = [f for f in os.listdir(backup_dir) if today in f]
    
    if len(backup_files) >= 2:  # حداقل دو فایل (اصلی و لاگ)
        logger.info(f"پشتیبان‌گیری امروز موجود است: {len(backup_files)} فایل")
        return True
    else:
        logger.warning("پشتیبان‌گیری امروز ناقص است")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # فقط بررسی وضعیت
        if check_backup_status():
            print("پشتیبان‌گیری به‌روز است")
            sys.exit(0)
        else:
            print("پشتیبان‌گیری نیاز به به‌روزرسانی دارد")
            sys.exit(1)
    else:
        # اجرای پشتیبان‌گیری
        if backup_databases():
            print("پشتیبان‌گیری موفق")
            sys.exit(0)
        else:
            print("خطا در پشتیبان‌گیری")
            sys.exit(1)
