#!/usr/bin/env python
"""
اسکریپت دیباگ مشکل dongle
این اسکریپت مشکل نوشتن روی فلش را بررسی می‌کند
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
import ctypes
import platform

def check_admin_privileges():
    """بررسی دسترسی ادمین"""
    print("🔍 بررسی دسترسی ادمین...")
    
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            print("✅ دسترسی ادمین تایید شد")
            return True
        else:
            print("❌ دسترسی ادمین ندارید")
            return False
    except Exception as e:
        print(f"❌ خطا در بررسی دسترسی ادمین: {e}")
        return False

def check_usb_drives():
    """بررسی درایوهای USB"""
    print("\n🔍 بررسی درایوهای USB...")
    
    try:
        usb_drives = dongle_manager.find_usb_drives()
        
        if not usb_drives:
            print("❌ هیچ درایو USB یافت نشد!")
            return None
        
        print(f"✅ {len(usb_drives)} درایو USB یافت شد:")
        for i, drive in enumerate(usb_drives, 1):
            print(f"   {i}. {drive['caption']} - {drive['drive_letter']} ({drive['device_id']})")
        
        return usb_drives
    except Exception as e:
        print(f"❌ خطا در یافتن درایوهای USB: {e}")
        return None

def check_lock_data():
    """بررسی اطلاعات قفل"""
    print("\n🔍 بررسی اطلاعات قفل...")
    
    try:
        latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
        
        if not latest_lock:
            print("❌ هیچ قفل فعالی یافت نشد!")
            return None
        
        print(f"✅ قفل فعال یافت شد:")
        print(f"   - ID: {latest_lock.id}")
        print(f"   - نام شرکت: {latest_lock.organization_name}")
        print(f"   - Salt: {latest_lock.salt}")
        print(f"   - Hash: {latest_lock.hash_value}")
        
        # رمزگشایی اطلاعات
        try:
            lock_expiry, lock_max_users, lock_org_name = latest_lock.get_decrypted_data()
            print(f"   - اطلاعات رمزگشایی شده:")
            print(f"     * تاریخ انقضا: {lock_expiry}")
            print(f"     * حداکثر کاربران: {lock_max_users}")
            print(f"     * نام شرکت: {lock_org_name}")
        except Exception as e:
            print(f"   ❌ خطا در رمزگشایی: {e}")
        
        return latest_lock
    except Exception as e:
        print(f"❌ خطا در بررسی قفل: {e}")
        return None

def test_sector_access(device_path):
    """تست دسترسی به سکتورها"""
    print(f"\n🔍 تست دسترسی به سکتورها برای {device_path}...")
    
    try:
        # تست خواندن سکتور
        print("   - تست خواندن سکتور 100...")
        data = dongle_manager.read_from_sector(device_path, 100)
        
        if data:
            print(f"   ✅ سکتور 100 قابل خواندن است ({len(data)} بایت)")
        else:
            print("   ❌ سکتور 100 قابل خواندن نیست")
        
        # تست نوشتن سکتور
        print("   - تست نوشتن سکتور 100...")
        test_data = b"TEST_DATA_FOR_DONGLE"
        success = dongle_manager.write_to_sector(device_path, 100, test_data)
        
        if success:
            print("   ✅ سکتور 100 قابل نوشتن است")
            
            # تست خواندن مجدد
            print("   - تست خواندن مجدد سکتور 100...")
            read_data = dongle_manager.read_from_sector(device_path, 100)
            
            if read_data and test_data in read_data:
                print("   ✅ داده‌ها با موفقیت نوشته و خوانده شدند")
                return True
            else:
                print("   ❌ داده‌ها نوشته شدند اما خوانده نشدند")
                return False
        else:
            print("   ❌ سکتور 100 قابل نوشتن نیست")
            return False
            
    except Exception as e:
        print(f"   ❌ خطا در تست سکتور: {e}")
        return False

def test_dongle_creation(device_path, lock_data):
    """تست ایجاد dongle"""
    print(f"\n🔍 تست ایجاد dongle برای {device_path}...")
    
    try:
        # دریافت اطلاعات قفل
        lock_expiry, lock_max_users, lock_org_name = lock_data.get_decrypted_data()
        
        print(f"   - اطلاعات قفل:")
        print(f"     * نام شرکت: {lock_org_name}")
        print(f"     * تاریخ انقضا: {lock_expiry}")
        print(f"     * حداکثر کاربران: {lock_max_users}")
        
        # ایجاد dongle
        print("   - ایجاد dongle...")
        success, message = dongle_manager.write_dongle_to_multiple_sectors(
            device_path,
            lock_data.lock_key.encode(),
            lock_org_name,
            "RCMS",
            lock_expiry
        )
        
        if success:
            print(f"   ✅ {message}")
            return True
        else:
            print(f"   ❌ {message}")
            return False
            
    except Exception as e:
        print(f"   ❌ خطا در ایجاد dongle: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔐 دیباگ مشکل USB Dongle")
    print("=" * 60)
    
    # بررسی دسترسی ادمین
    if not check_admin_privileges():
        print("\n❌ مشکل: دسترسی ادمین ندارید!")
        print("راه‌حل: Django را به عنوان Administrator اجرا کنید")
        return False
    
    # بررسی درایوهای USB
    usb_drives = check_usb_drives()
    if not usb_drives:
        print("\n❌ مشکل: هیچ درایو USB یافت نشد!")
        print("راه‌حل: یک فلش USB را به سیستم متصل کنید")
        return False
    
    # بررسی اطلاعات قفل
    lock_data = check_lock_data()
    if not lock_data:
        print("\n❌ مشکل: هیچ قفل فعالی یافت نشد!")
        print("راه‌حل: ابتدا یک قفل ایجاد کنید")
        return False
    
    # تست دسترسی به سکتورها
    device_path = usb_drives[0]['device_id']
    if not test_sector_access(device_path):
        print("\n❌ مشکل: دسترسی به سکتورها ندارید!")
        print("راه‌حل:")
        print("1. اطمینان حاصل کنید که Django به عنوان Administrator اجرا شده")
        print("2. فلش را eject و دوباره متصل کنید")
        print("3. از فلش دیگری استفاده کنید")
        print("4. Windows Defender را موقتاً غیرفعال کنید")
        return False
    
    # تست ایجاد dongle
    if not test_dongle_creation(device_path, lock_data):
        print("\n❌ مشکل: dongle ایجاد نشد!")
        print("راه‌حل:")
        print("1. اطمینان حاصل کنید که Django به عنوان Administrator اجرا شده")
        print("2. فلش را فرمت کنید (FAT32)")
        print("3. از فلش دیگری استفاده کنید")
        return False
    
    print("\n✅ همه تست‌ها موفق بود!")
    print("🎉 سیستم dongle آماده استفاده است!")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
