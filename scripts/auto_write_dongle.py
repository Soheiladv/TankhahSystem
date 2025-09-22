#!/usr/bin/env python
"""
اسکریپت خودکار نوشتن dongle
این اسکریپت اطلاعات قفل را از فایل کد شده خوانده و روی فلش می‌نویسد
"""

import os
import sys
import django
import json
import base64
import hashlib
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from usb_key_validator.enhanced_utils import dongle_manager

def load_lock_config():
    """بارگذاری اطلاعات قفل از فایل کد شده"""
    print("📂 بارگذاری اطلاعات قفل از فایل کد شده...")
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'lock_config.json')
        
        if not os.path.exists(config_path):
            print("❌ فایل کد شده یافت نشد!")
            print("ابتدا اسکریپت save_lock_config.py را اجرا کنید")
            return None
        
        # خواندن فایل
        with open(config_path, 'r', encoding='utf-8') as f:
            config_file = json.load(f)
        
        # بررسی checksum
        data = config_file['data']
        expected_checksum = hashlib.sha256(data.encode()).hexdigest()
        
        if config_file['checksum'] != expected_checksum:
            print("❌ فایل کد شده خراب است!")
            return None
        
        # رمزگشایی اطلاعات
        config_json = base64.b64decode(data).decode('utf-8')
        lock_config = json.loads(config_json)
        
        print(f"✅ اطلاعات قفل بارگذاری شد:")
        print(f"   - نام شرکت: {lock_config['organization_name']}")
        print(f"   - شناسه نرم‌افزار: {lock_config['software_id']}")
        print(f"   - تاریخ انقضا: {lock_config['expiry_date']}")
        print(f"   - حداکثر کاربران: {lock_config['max_users']}")
        
        return lock_config
        
    except Exception as e:
        print(f"❌ خطا در بارگذاری اطلاعات: {e}")
        return None

def find_usb_drives():
    """یافتن درایوهای USB"""
    print("\n🔍 یافتن درایوهای USB...")
    
    try:
        usb_drives = dongle_manager.find_usb_drives()
        
        if not usb_drives:
            print("❌ هیچ درایو USB یافت نشد!")
            print("لطفاً یک فلش USB را به سیستم متصل کنید")
            return None
        
        print(f"✅ {len(usb_drives)} درایو USB یافت شد:")
        for i, drive in enumerate(usb_drives, 1):
            print(f"   {i}. {drive['caption']} - {drive['drive_letter']} ({drive['device_id']})")
        
        return usb_drives
        
    except Exception as e:
        print(f"❌ خطا در یافتن درایوهای USB: {e}")
        return None

def write_dongle_to_usb(device_path, lock_config):
    """نوشتن dongle روی فلش"""
    print(f"\n✍️ نوشتن dongle روی فلش {device_path}...")
    
    try:
        # تبدیل تاریخ انقضا
        expiry_date = None
        if lock_config['expiry_date']:
            from datetime import datetime
            expiry_date = datetime.fromisoformat(lock_config['expiry_date']).date()
        
        # نوشتن dongle
        success, message = dongle_manager.write_dongle_to_multiple_sectors(
            device_path,
            lock_config['lock_key'].encode(),
            lock_config['organization_name'],
            lock_config['software_id'],
            expiry_date
        )
        
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در نوشتن dongle: {e}")
        return False

def validate_dongle(device_path):
    """اعتبارسنجی dongle"""
    print(f"\n🔍 اعتبارسنجی dongle...")
    
    try:
        is_valid, message = dongle_manager.validate_dongle_integrity(device_path)
        
        if is_valid:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در اعتبارسنجی: {e}")
        return False

def get_dongle_stats(device_path):
    """دریافت آمار dongle"""
    print(f"\n📊 دریافت آمار dongle...")
    
    try:
        stats = dongle_manager.get_dongle_statistics(device_path)
        
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
            
            return True
        else:
            print("❌ آمار dongle در دسترس نیست")
            return False
            
    except Exception as e:
        print(f"❌ خطا در دریافت آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🚀 اسکریپت خودکار نوشتن USB Dongle")
    print("=" * 60)
    
    # بارگذاری اطلاعات قفل
    lock_config = load_lock_config()
    if not lock_config:
        return False
    
    # یافتن درایوهای USB
    usb_drives = find_usb_drives()
    if not usb_drives:
        return False
    
    # انتخاب اولین درایو
    device_path = usb_drives[0]['device_id']
    print(f"\n🎯 استفاده از درایو: {device_path}")
    
    # نوشتن dongle
    if not write_dongle_to_usb(device_path, lock_config):
        return False
    
    # اعتبارسنجی dongle
    if not validate_dongle(device_path):
        return False
    
    # دریافت آمار
    get_dongle_stats(device_path)
    
    print(f"\n🎉 dongle با موفقیت ایجاد شد!")
    print(f"✅ فلش USB حالا به عنوان dongle عمل می‌کند")
    print(f"✅ اطلاعات قفل در سکتورهای مخفی ذخیره شد")
    print(f"✅ سیستم خودکار در هر لاگین چک می‌کند")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
