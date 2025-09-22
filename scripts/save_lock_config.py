#!/usr/bin/env python
"""
اسکریپت ذخیره اطلاعات قفل در فایل کد شده
این اسکریپت اطلاعات قفل را در یک فایل JSON کد شده ذخیره می‌کند
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

from accounts.models import TimeLockModel

def save_lock_config():
    """ذخیره اطلاعات قفل در فایل کد شده"""
    print("💾 ذخیره اطلاعات قفل در فایل کد شده...")
    print("=" * 60)
    
    try:
        # دریافت آخرین قفل فعال
        latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
        
        if not latest_lock:
            print("❌ هیچ قفل فعالی یافت نشد!")
            print("ابتدا یک قفل ایجاد کنید: http://127.0.0.1:8000/accounts/set_time_lock/")
            return False
        
        # رمزگشایی اطلاعات قفل
        try:
            lock_expiry, lock_max_users, lock_org_name = latest_lock.get_decrypted_data()
        except Exception as e:
            print(f"❌ خطا در رمزگشایی قفل: {e}")
            return False
        
        # ایجاد اطلاعات قفل
        lock_config = {
            'organization_name': lock_org_name,
            'software_id': 'RCMS',
            'expiry_date': lock_expiry.isoformat() if lock_expiry else None,
            'max_users': lock_max_users,
            'lock_key': latest_lock.lock_key,
            'salt': latest_lock.salt,
            'hash_value': latest_lock.hash_value,
            'created_at': latest_lock.created_at.isoformat(),
            'version': '2.0',
            'description': 'USB Dongle Configuration - Auto Generated'
        }
        
        # کد کردن اطلاعات
        config_json = json.dumps(lock_config, ensure_ascii=False, indent=2)
        config_encoded = base64.b64encode(config_json.encode('utf-8')).decode('utf-8')
        
        # ایجاد checksum
        checksum = hashlib.sha256(config_encoded.encode()).hexdigest()
        
        # ایجاد فایل کد شده
        config_file = {
            'checksum': checksum,
            'data': config_encoded,
            'created_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        # ذخیره فایل
        config_path = os.path.join(os.path.dirname(__file__), 'lock_config.json')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_file, f, ensure_ascii=False, indent=2)
        
        print(f"✅ اطلاعات قفل در فایل ذخیره شد: {config_path}")
        print(f"\n📋 اطلاعات ذخیره شده:")
        print(f"   - نام شرکت: {lock_org_name}")
        print(f"   - شناسه نرم‌افزار: RCMS")
        print(f"   - تاریخ انقضا: {lock_expiry}")
        print(f"   - حداکثر کاربران: {lock_max_users}")
        print(f"   - Checksum: {checksum[:16]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ذخیره اطلاعات: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔐 ذخیره اطلاعات قفل برای USB Dongle")
    print("=" * 60)
    
    if save_lock_config():
        print(f"\n🎉 اطلاعات قفل با موفقیت ذخیره شد!")
        print(f"\n📁 فایل کد شده: scripts/lock_config.json")
        print(f"🔧 برای نوشتن قفل روی فلش از اسکریپت زیر استفاده کنید:")
        print(f"   python scripts/auto_write_dongle.py")
    else:
        print(f"\n❌ خطا در ذخیره اطلاعات!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
