#!/usr/bin/env python
"""
اسکریپت تست برای سیستم پشتیبان‌گیری
"""

import os
import sys
import django
from pathlib import Path

# اضافه کردن مسیر scripts به Python path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from config import (
    get_project_root, get_django_settings, ensure_logs_dir
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

def test_models():
    """تست مدل‌های جدید"""
    print("🔍 تست مدل‌های جدید...")
    
    try:
        from notificationApp.models import BackupSchedule, BackupLog, Notification
        
        # تست ایجاد اسکچول
        print("✅ مدل‌های BackupSchedule, BackupLog, Notification بارگذاری شدند")
        
        # شمارش اسکچول‌های موجود
        schedule_count = BackupSchedule.objects.count()
        log_count = BackupLog.objects.count()
        notification_count = Notification.objects.count()
        
        print(f"📊 آمار موجود:")
        print(f"   - اسکچول‌های پشتیبان‌گیری: {schedule_count}")
        print(f"   - لاگ‌های پشتیبان‌گیری: {log_count}")
        print(f"   - اعلان‌ها: {notification_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست مدل‌ها: {str(e)}")
        return False

def test_utils():
    """تست توابع utils"""
    print("\n🔍 تست توابع utils...")
    
    try:
        from notificationApp.utils import (
            send_backup_notification, 
            execute_scheduled_backup,
            check_and_execute_scheduled_backups
        )
        
        print("✅ توابع utils بارگذاری شدند")
        
        # تست تابع check_and_execute_scheduled_backups
        print("🔄 تست تابع check_and_execute_scheduled_backups...")
        check_and_execute_scheduled_backups()
        print("✅ تابع check_and_execute_scheduled_backups اجرا شد")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست utils: {str(e)}")
        return False

def test_admin():
    """تست admin interface"""
    print("\n🔍 تست admin interface...")
    
    try:
        from notificationApp.admin import (
            BackupScheduleAdmin, 
            BackupLogAdmin, 
            NotificationAdmin
        )
        
        print("✅ کلاس‌های admin بارگذاری شدند")
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست admin: {str(e)}")
        return False

def test_management_commands():
    """تست management commands"""
    print("\n🔍 تست management commands...")
    
    try:
        from django.core.management import call_command
        
        # تست command run_backup_scheduler
        print("🔄 تست command run_backup_scheduler...")
        call_command('run_backup_scheduler', '--dry-run')
        print("✅ command run_backup_scheduler اجرا شد")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست management commands: {str(e)}")
        return False

def main():
    """تابع اصلی تست"""
    print("🚀 شروع تست سیستم پشتیبان‌گیری...")
    
    # تنظیم Django
    setup_django()
    
    # ایجاد پوشه logs
    ensure_logs_dir()
    
    # اجرای تست‌ها
    tests = [
        ("مدل‌ها", test_models),
        ("توابع utils", test_utils),
        ("Admin interface", test_admin),
        ("Management commands", test_management_commands),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ خطا در تست {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # نمایش نتایج
    print("\n" + "="*50)
    print("📋 نتایج تست‌ها:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"📊 نتیجه نهایی: {passed}/{len(results)} تست موفق")
    
    if passed == len(results):
        print("🎉 همه تست‌ها موفق بودند!")
        return 0
    else:
        print("⚠️ برخی تست‌ها ناموفق بودند!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
