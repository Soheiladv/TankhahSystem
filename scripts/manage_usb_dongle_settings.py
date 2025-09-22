#!/usr/bin/env python
"""
مدیریت تنظیمات USB dongle
این اسکریپت تنظیمات USB dongle را مدیریت می‌کند
"""

import os
import sys
import django
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.conf import settings

def show_current_settings():
    """نمایش تنظیمات فعلی USB dongle"""
    
    print("⚙️ تنظیمات فعلی USB dongle:")
    print("=" * 50)
    
    settings_list = [
        ('USB_DONGLE_VALIDATION_ENABLED', 'اعتبارسنجی فعال'),
        ('USB_DONGLE_CACHE_TIMEOUT', 'مدت زمان cache (ثانیه)'),
        ('USB_DONGLE_NOTIFICATIONS_ENABLED', 'اعلان‌ها فعال'),
        ('USB_DONGLE_DEBUG_MODE', 'حالت دیباگ'),
    ]
    
    for setting_name, description in settings_list:
        value = getattr(settings, setting_name, 'تعریف نشده')
        print(f"   {description}: {value}")
    
    # بررسی middleware
    middleware_list = getattr(settings, 'MIDDLEWARE', [])
    usb_middleware_active = any('USBDongleValidationMiddleware' in middleware for middleware in middleware_list)
    print(f"\n   Middleware فعال: {'✅ بله' if usb_middleware_active else '❌ خیر'}")

def create_env_file():
    """ایجاد فایل .env با تنظیمات USB dongle"""
    
    print("\n📝 ایجاد فایل .env:")
    print("=" * 30)
    
    env_content = """# تنظیمات USB Dongle Validation
# فعال/غیرفعال کردن اعتبارسنجی USB dongle
# true = فعال، false = غیرفعال
USB_DONGLE_VALIDATION_ENABLED=false

# تنظیمات اضافی USB dongle
# مدت زمان cache اعتبارسنجی (ثانیه)
USB_DONGLE_CACHE_TIMEOUT=300

# فعال/غیرفعال کردن اعلان‌های USB dongle
USB_DONGLE_NOTIFICATIONS_ENABLED=true

# تنظیمات لاگ
USB_DONGLE_DEBUG_MODE=false
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ فایل .env ایجاد شد")
        print("\n📋 محتوای فایل .env:")
        print(env_content)
    except Exception as e:
        print(f"❌ خطا در ایجاد فایل .env: {e}")

def show_usage_guide():
    """نمایش راهنمای استفاده"""
    
    print("\n📖 راهنمای استفاده:")
    print("=" * 30)
    
    print("🔧 برای فعال کردن اعتبارسنجی USB dongle:")
    print("   1. فایل .env را ویرایش کنید")
    print("   2. USB_DONGLE_VALIDATION_ENABLED=true را تنظیم کنید")
    print("   3. Django را restart کنید")
    
    print("\n🚫 برای غیرفعال کردن اعتبارسنجی USB dongle:")
    print("   1. فایل .env را ویرایش کنید")
    print("   2. USB_DONGLE_VALIDATION_ENABLED=false را تنظیم کنید")
    print("   3. Django را restart کنید")
    
    print("\n⚙️ تنظیمات اضافی:")
    print("   - USB_DONGLE_CACHE_TIMEOUT: مدت زمان cache (پیش‌فرض: 300 ثانیه)")
    print("   - USB_DONGLE_NOTIFICATIONS_ENABLED: اعلان‌ها (پیش‌فرض: true)")
    print("   - USB_DONGLE_DEBUG_MODE: حالت دیباگ (پیش‌فرض: false)")

def test_settings():
    """تست تنظیمات"""
    
    print("\n🧪 تست تنظیمات:")
    print("=" * 20)
    
    # تست فعال بودن اعتبارسنجی
    validation_enabled = getattr(settings, 'USB_DONGLE_VALIDATION_ENABLED', False)
    print(f"اعتبارسنجی فعال: {'✅ بله' if validation_enabled else '❌ خیر'}")
    
    if not validation_enabled:
        print("ℹ️ اعتبارسنجی USB dongle غیرفعال است")
        print("   کاربران می‌توانند بدون مشکل وارد سیستم شوند")
    else:
        print("⚠️ اعتبارسنجی USB dongle فعال است")
        print("   کاربران نیاز به USB dongle معتبر دارند")
    
    # تست middleware
    middleware_list = getattr(settings, 'MIDDLEWARE', [])
    usb_middleware_active = any('USBDongleValidationMiddleware' in middleware for middleware in middleware_list)
    print(f"Middleware فعال: {'✅ بله' if usb_middleware_active else '❌ خیر'}")
    
    if usb_middleware_active and not validation_enabled:
        print("ℹ️ Middleware فعال است اما اعتبارسنجی غیرفعال")
        print("   Middleware کار نمی‌کند")
    elif usb_middleware_active and validation_enabled:
        print("✅ Middleware و اعتبارسنجی هر دو فعال هستند")
    elif not usb_middleware_active:
        print("⚠️ Middleware غیرفعال است")

def show_user_impact():
    """نمایش تأثیر بر کاربران"""
    
    print("\n👥 تأثیر بر کاربران:")
    print("=" * 25)
    
    validation_enabled = getattr(settings, 'USB_DONGLE_VALIDATION_ENABLED', False)
    
    if not validation_enabled:
        print("✅ همه کاربران می‌توانند بدون مشکل وارد شوند")
        print("   - کاربر snejate: بدون مشکل")
        print("   - سایر کاربران: بدون مشکل")
        print("   - نیازی به USB dongle نیست")
    else:
        print("⚠️ کاربران نیاز به USB dongle معتبر دارند")
        print("   - کاربر snejate: نیاز به USB dongle")
        print("   - سایر کاربران: نیاز به USB dongle")
        print("   - در صورت عدم وجود dongle: ریدایرکت به صفحه اعتبارسنجی")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='مدیریت تنظیمات USB dongle')
    parser.add_argument('--create-env', action='store_true', help='ایجاد فایل .env')
    parser.add_argument('--test', action='store_true', help='تست تنظیمات')
    parser.add_argument('--guide', action='store_true', help='نمایش راهنما')
    parser.add_argument('--impact', action='store_true', help='نمایش تأثیر بر کاربران')
    
    args = parser.parse_args()
    
    if args.create_env:
        create_env_file()
    elif args.test:
        test_settings()
    elif args.guide:
        show_usage_guide()
    elif args.impact:
        show_user_impact()
    else:
        show_current_settings()
        test_settings()
        show_user_impact()
        show_usage_guide()
