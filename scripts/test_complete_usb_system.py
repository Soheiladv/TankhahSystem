#!/usr/bin/env python
"""
تست کامل سیستم USB dongle
این اسکریپت تمام جنبه‌های سیستم USB dongle را تست می‌کند
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
from django.contrib.auth import get_user_model
from usb_key_validator.enhanced_utils import dongle_manager

User = get_user_model()

def test_usb_system_complete():
    """تست کامل سیستم USB dongle"""
    
    print("🔍 تست کامل سیستم USB dongle")
    print("=" * 60)
    
    # 1. تست تنظیمات
    print("1️⃣ تست تنظیمات:")
    print("   " + "-" * 40)
    
    validation_enabled = getattr(settings, 'USB_DONGLE_VALIDATION_ENABLED', False)
    cache_timeout = getattr(settings, 'USB_DONGLE_CACHE_TIMEOUT', 300)
    notifications_enabled = getattr(settings, 'USB_DONGLE_NOTIFICATIONS_ENABLED', True)
    debug_mode = getattr(settings, 'USB_DONGLE_DEBUG_MODE', False)
    
    print(f"   اعتبارسنجی فعال: {'✅ بله' if validation_enabled else '❌ خیر'}")
    print(f"   مدت زمان cache: {cache_timeout} ثانیه")
    print(f"   اعلان‌ها فعال: {'✅ بله' if notifications_enabled else '❌ خیر'}")
    print(f"   حالت دیباگ: {'✅ بله' if debug_mode else '❌ خیر'}")
    
    # 2. تست middleware
    print(f"\n2️⃣ تست middleware:")
    print("   " + "-" * 40)
    
    middleware_list = getattr(settings, 'MIDDLEWARE', [])
    usb_middleware_active = any('USBDongleValidationMiddleware' in middleware for middleware in middleware_list)
    print(f"   Middleware فعال: {'✅ بله' if usb_middleware_active else '❌ خیر'}")
    
    if usb_middleware_active and not validation_enabled:
        print("   ℹ️ Middleware فعال اما اعتبارسنجی غیرفعال - کار نمی‌کند")
    elif usb_middleware_active and validation_enabled:
        print("   ✅ Middleware و اعتبارسنجی هر دو فعال")
    elif not usb_middleware_active:
        print("   ⚠️ Middleware غیرفعال")
    
    # 3. تست USB drives
    print(f"\n3️⃣ تست USB drives:")
    print("   " + "-" * 40)
    
    try:
        usb_drives = dongle_manager.find_usb_drives()
        if usb_drives:
            print(f"   ✅ {len(usb_drives)} USB drive یافت شد:")
            for drive in usb_drives:
                print(f"      - {drive['device_id']}: {drive['size']} GB")
        else:
            print("   ❌ هیچ USB drive یافت نشد")
    except Exception as e:
        print(f"   ❌ خطا در یافتن USB drives: {e}")
    
    # 4. تست اعتبارسنجی
    print(f"\n4️⃣ تست اعتبارسنجی:")
    print("   " + "-" * 40)
    
    if validation_enabled:
        try:
            result = dongle_manager.daily_validation_check()
            print(f"   وضعیت: {'✅ معتبر' if result['valid'] else '❌ نامعتبر'}")
            print(f"   پیام: {result['message']}")
        except Exception as e:
            print(f"   ❌ خطا در اعتبارسنجی: {e}")
    else:
        print("   ℹ️ اعتبارسنجی غیرفعال - تست نشد")
    
    # 5. تست کاربران
    print(f"\n5️⃣ تست کاربران:")
    print("   " + "-" * 40)
    
    try:
        test_users = ['admin', 'snejate', 'beygh']
        for username in test_users:
            try:
                user = User.objects.get(username=username)
                print(f"   {username}: {'✅ superuser' if user.is_superuser else '👤 کاربر عادی'}")
            except User.DoesNotExist:
                print(f"   {username}: ❌ یافت نشد")
    except Exception as e:
        print(f"   ❌ خطا در دسترسی به دیتابیس: {e}")
        print("   ℹ️ تست کاربران رد شد")
    
    # 6. تست تأثیر بر کاربران
    print(f"\n6️⃣ تأثیر بر کاربران:")
    print("   " + "-" * 40)
    
    if not validation_enabled:
        print("   ✅ همه کاربران می‌توانند بدون مشکل وارد شوند")
        print("   ✅ کاربر snejate: بدون مشکل")
        print("   ✅ سایر کاربران: بدون مشکل")
    else:
        print("   ⚠️ کاربران نیاز به USB dongle معتبر دارند")
        print("   ⚠️ کاربر snejate: نیاز به USB dongle")
        print("   ⚠️ سایر کاربران: نیاز به USB dongle")

def show_recommendations():
    """نمایش توصیه‌ها"""
    
    print(f"\n💡 توصیه‌ها:")
    print("=" * 30)
    
    validation_enabled = getattr(settings, 'USB_DONGLE_VALIDATION_ENABLED', False)
    
    if not validation_enabled:
        print("✅ وضعیت فعلی مناسب است:")
        print("   - اعتبارسنجی غیرفعال")
        print("   - همه کاربران بدون مشکل وارد می‌شوند")
        print("   - کاربر snejate مشکل ندارد")
        
        print(f"\n🔧 برای فعال کردن اعتبارسنجی:")
        print("   python scripts/toggle_usb_validation.py --enable")
        print("   سپس Django را restart کنید")
    else:
        print("⚠️ اعتبارسنجی فعال است:")
        print("   - کاربران نیاز به USB dongle دارند")
        print("   - ممکن است مشکلات دسترسی وجود داشته باشد")
        
        print(f"\n🔧 برای غیرفعال کردن اعتبارسنجی:")
        print("   python scripts/toggle_usb_validation.py --disable")
        print("   سپس Django را restart کنید")

def show_quick_commands():
    """نمایش دستورات سریع"""
    
    print(f"\n⚡ دستورات سریع:")
    print("=" * 25)
    print("python scripts/toggle_usb_validation.py --status     # وضعیت فعلی")
    print("python scripts/toggle_usb_validation.py --enable     # فعال کردن")
    print("python scripts/toggle_usb_validation.py --disable    # غیرفعال کردن")
    print("python scripts/manage_usb_dongle_settings.py         # مدیریت تنظیمات")

if __name__ == "__main__":
    test_usb_system_complete()
    show_recommendations()
    show_quick_commands()
