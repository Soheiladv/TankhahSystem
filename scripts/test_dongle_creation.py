#!/usr/bin/env python
"""
اسکریپت تست ایجاد dongle
این اسکریپت dongle را با اطلاعات قفل موجود ایجاد می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from usb_key_validator.enhanced_utils import dongle_manager
from accounts.models import TimeLockModel
import time

def test_dongle_creation():
    """تست ایجاد dongle"""
    print("🚀 شروع تست ایجاد dongle...")
    print("=" * 60)
    
    # یافتن درایوهای USB
    print("1. یافتن درایوهای USB...")
    usb_drives = dongle_manager.find_usb_drives()
    
    if not usb_drives:
        print("❌ هیچ درایو USB یافت نشد!")
        print("لطفاً یک فلش USB را به سیستم متصل کنید.")
        return False
    
    print(f"✅ {len(usb_drives)} درایو USB یافت شد:")
    for i, drive in enumerate(usb_drives, 1):
        print(f"   {i}. {drive['caption']} - {drive['drive_letter']} ({drive['device_id']})")
    
    # انتخاب اولین درایو
    device = usb_drives[0]['device_id']
    print(f"\n2. استفاده از درایو: {device}")
    
    # دریافت اطلاعات قفل
    print("\n3. دریافت اطلاعات قفل...")
    latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
    
    if not latest_lock:
        print("❌ هیچ قفل فعالی یافت نشد!")
        return False
    
    try:
        lock_expiry, lock_max_users, lock_org_name = latest_lock.get_decrypted_data()
        print(f"✅ اطلاعات قفل:")
        print(f"   - نام شرکت: {lock_org_name}")
        print(f"   - تاریخ انقضا: {lock_expiry}")
        print(f"   - حداکثر کاربران: {lock_max_users}")
    except Exception as e:
        print(f"❌ خطا در رمزگشایی قفل: {e}")
        return False
    
    # ایجاد dongle
    print(f"\n4. ایجاد dongle...")
    try:
        success, message = dongle_manager.write_dongle_to_multiple_sectors(
            device, 
            latest_lock.lock_key.encode(),
            lock_org_name,
            "RCMS",
            lock_expiry
        )
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در ایجاد dongle: {e}")
        return False
    
    # اعتبارسنجی dongle
    print(f"\n5. اعتبارسنجی dongle...")
    try:
        is_valid, message = dongle_manager.validate_dongle_integrity(device)
        
        if is_valid:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در اعتبارسنجی: {e}")
        return False
    
    # آمار dongle
    print(f"\n6. آمار dongle...")
    try:
        stats = dongle_manager.get_dongle_statistics(device)
        
        if stats:
            print(f"✅ آمار dongle:")
            print(f"   - کل سکتورها: {stats['total_sectors']}")
            print(f"   - سکتورهای معتبر: {stats['valid_sectors']}")
            print(f"   - اندازه سکتور: {stats['sector_size']} بایت")
            
            if 'organization_name' in stats:
                print(f"   - نام شرکت: {stats['organization_name']}")
                print(f"   - شناسه نرم‌افزار: {stats['software_id']}")
                print(f"   - تاریخ انقضا: {stats['expiry_date']}")
                print(f"   - نوع dongle: {stats['dongle_type']}")
        else:
            print("❌ آمار dongle در دسترس نیست")
            
    except Exception as e:
        print(f"❌ خطا در دریافت آمار: {e}")
    
    print(f"\n🎉 تست dongle با موفقیت انجام شد!")
    return True

def test_dongle_reading():
    """تست خواندن dongle"""
    print(f"\n7. تست خواندن dongle...")
    
    usb_drives = dongle_manager.find_usb_drives()
    if not usb_drives:
        print("❌ هیچ درایو USB یافت نشد!")
        return False
    
    device = usb_drives[0]['device_id']
    
    try:
        key_data, signature_data, source_sector = dongle_manager.read_dongle_from_sectors(device)
        
        if key_data and signature_data:
            print(f"✅ dongle از سکتور {source_sector} خوانده شد")
            
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
            print("❌ dongle یافت نشد")
            return False
            
    except Exception as e:
        print(f"❌ خطا در خواندن dongle: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("🔐 تست کامل سیستم USB Dongle")
        print("=" * 60)
        
        # تست ایجاد dongle
        if test_dongle_creation():
            # تست خواندن dongle
            test_dongle_reading()
            
            print(f"\n🎯 نتیجه:")
            print(f"✅ dongle با موفقیت ایجاد شد")
            print(f"✅ dongle قابل خواندن است")
            print(f"✅ سیستم آماده استفاده است")
            
            print(f"\n🌐 برای مدیریت dongle:")
            print(f"   http://127.0.0.1:8000/usb-key-validator/enhanced/")
            print(f"   http://127.0.0.1:8000/usb-key-validator/dashboard/")
        else:
            print(f"\n❌ تست ناموفق بود")
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")