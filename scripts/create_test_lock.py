#!/usr/bin/env python
"""
اسکریپت ایجاد قفل تست برای USB Dongle
این اسکریپت یک قفل تست ایجاد می‌کند تا بتوان dongle ایجاد کرد
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from core.RCMS_Lock.security import TimeLock
from datetime import date, timedelta

def create_test_lock():
    """ایجاد قفل تست"""
    print("🔧 ایجاد قفل تست برای USB Dongle...")
    print("=" * 50)
    
    # اطلاعات قفل تست
    company_name = "شرکت تست"
    max_users = 10
    expiry_days = 365
    
    # محاسبه تاریخ انقضا
    expiry_date = date.today() + timedelta(days=expiry_days)
    
    print(f"اطلاعات قفل تست:")
    print(f"   - نام شرکت: {company_name}")
    print(f"   - حداکثر کاربران: {max_users}")
    print(f"   - مدت اعتبار: {expiry_days} روز")
    print(f"   - تاریخ انقضا: {expiry_date}")
    
    # ایجاد قفل
    print(f"\nایجاد قفل...")
    success = TimeLock.set_expiry_date(expiry_date, max_users, company_name)
    
    if success:
        print("✅ قفل تست با موفقیت ایجاد شد!")
        
        # بررسی قفل ایجاد شده
        print(f"\nبررسی قفل ایجاد شده:")
        created_expiry = TimeLock.get_expiry_date()
        created_max_users = TimeLock.get_max_users()
        created_org_name = TimeLock.get_organization_name()
        
        print(f"   - تاریخ انقضا: {created_expiry}")
        print(f"   - حداکثر کاربران: {created_max_users}")
        print(f"   - نام شرکت: {created_org_name}")
        
        print(f"\nحالا می‌توانید dongle ایجاد کنید:")
        print(f"   python scripts/test_dongle_creation.py")
        
        return True
    else:
        print("❌ خطا در ایجاد قفل تست!")
        return False

def check_existing_locks():
    """بررسی قفل‌های موجود"""
    print("🔍 بررسی قفل‌های موجود...")
    
    from accounts.models import TimeLockModel
    
    locks = TimeLockModel.objects.filter(is_active=True).order_by('-created_at')
    
    if locks.exists():
        print(f"✅ {locks.count()} قفل فعال یافت شد:")
        for lock in locks:
            expiry_date, max_users, org_name = lock.get_decrypted_data()
            print(f"   - ID: {lock.id}")
            print(f"     نام شرکت: {org_name}")
            print(f"     تاریخ انقضا: {expiry_date}")
            print(f"     حداکثر کاربران: {max_users}")
            print(f"     تاریخ ایجاد: {lock.created_at}")
            print()
    else:
        print("❌ هیچ قفل فعالی یافت نشد!")
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 شروع مدیریت قفل‌های USB Dongle...")
        
        # بررسی قفل‌های موجود
        if not check_existing_locks():
            # ایجاد قفل تست
            create_test_lock()
        else:
            print("✅ قفل‌های فعال موجود است. می‌توانید dongle ایجاد کنید.")
            print(f"   python scripts/test_dongle_creation.py")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
