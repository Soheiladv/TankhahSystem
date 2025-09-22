#!/usr/bin/env python
"""
اسکریپت بررسی اطلاعات قفل
این اسکریپت اطلاعات قفل موجود در دیتابیس را نمایش می‌دهد
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from accounts.models import TimeLockModel
from core.RCMS_Lock.security import TimeLock
import jdatetime

def check_lock_info():
    """بررسی اطلاعات قفل"""
    print("🔍 بررسی اطلاعات قفل موجود...")
    print("=" * 60)
    
    # بررسی قفل‌های موجود در دیتابیس
    print("1. قفل‌های موجود در دیتابیس:")
    locks = TimeLockModel.objects.filter(is_active=True).order_by('-created_at')
    
    if locks.exists():
        print(f"✅ {locks.count()} قفل فعال یافت شد:")
        for i, lock in enumerate(locks, 1):
            print(f"\n   قفل {i}:")
            print(f"   - ID: {lock.id}")
            print(f"   - نام شرکت: {lock.organization_name}")
            print(f"   - Salt: {lock.salt}")
            print(f"   - Hash: {lock.hash_value}")
            print(f"   - تاریخ ایجاد: {lock.created_at}")
            print(f"   - وضعیت: {'فعال' if lock.is_active else 'غیرفعال'}")
            
            # رمزگشایی اطلاعات
            try:
                expiry_date, max_users, org_name = lock.get_decrypted_data()
                print(f"   - اطلاعات رمزگشایی شده:")
                print(f"     * تاریخ انقضا: {expiry_date}")
                print(f"     * حداکثر کاربران: {max_users}")
                print(f"     * نام شرکت: {org_name}")
                
                # تبدیل تاریخ به شمسی
                if expiry_date:
                    jalali_date = jdatetime.date.fromgregorian(date=expiry_date)
                    print(f"     * تاریخ انقضا (شمسی): {jalali_date.strftime('%Y/%m/%d')}")
                
            except Exception as e:
                print(f"   ❌ خطا در رمزگشایی: {e}")
    else:
        print("❌ هیچ قفل فعالی یافت نشد!")
        return False
    
    # بررسی از طریق TimeLock
    print(f"\n2. بررسی از طریق TimeLock:")
    try:
        expiry_date = TimeLock.get_expiry_date()
        max_users = TimeLock.get_max_users()
        org_name = TimeLock.get_organization_name()
        
        print(f"   - تاریخ انقضا: {expiry_date}")
        print(f"   - حداکثر کاربران: {max_users}")
        print(f"   - نام شرکت: {org_name}")
        
        if expiry_date:
            jalali_date = jdatetime.date.fromgregorian(date=expiry_date)
            print(f"   - تاریخ انقضا (شمسی): {jalali_date.strftime('%Y/%m/%d')}")
        
    except Exception as e:
        print(f"   ❌ خطا در دریافت اطلاعات از TimeLock: {e}")
    
    # بررسی وضعیت قفل
    print(f"\n3. وضعیت قفل:")
    try:
        is_locked = TimeLock.is_locked()
        print(f"   - وضعیت: {'قفل شده' if is_locked else 'باز'}")
    except Exception as e:
        print(f"   ❌ خطا در بررسی وضعیت قفل: {e}")
    
    return True

def test_dongle_with_lock():
    """تست dongle با اطلاعات قفل"""
    print(f"\n4. تست dongle با اطلاعات قفل:")
    
    from usb_key_validator.enhanced_utils import dongle_manager
    
    # یافتن درایوهای USB
    usb_drives = dongle_manager.find_usb_drives()
    if not usb_drives:
        print("❌ هیچ درایو USB یافت نشد!")
        return False
    
    device = usb_drives[0]['device_id']
    print(f"   - استفاده از درایو: {device}")
    
    # خواندن dongle
    key_data, signature_data, source_sector = dongle_manager.read_dongle_from_sectors(device)
    
    if key_data and signature_data:
        print(f"   ✅ dongle یافت شد از سکتور {source_sector}")
        
        if isinstance(signature_data, dict):
            print(f"   - اطلاعات dongle:")
            print(f"     * نام شرکت: {signature_data.get('organization_name', 'نامشخص')}")
            print(f"     * شناسه نرم‌افزار: {signature_data.get('software_id', 'نامشخص')}")
            print(f"     * تاریخ انقضا: {signature_data.get('expiry_date', 'نامشخص')}")
            print(f"     * نوع dongle: {signature_data.get('dongle_type', 'نامشخص')}")
            print(f"     * شناسه دستگاه: {signature_data.get('device_id', 'نامشخص')}")
        else:
            print(f"   - فرمت قدیمی dongle")
    else:
        print(f"   ❌ dongle یافت نشد")
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 شروع بررسی اطلاعات قفل...")
        
        # بررسی اطلاعات قفل
        if check_lock_info():
            # تست dongle
            test_dongle_with_lock()
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
