#!/usr/bin/env python
"""
بررسی وضعیت USB dongle و middleware
این اسکریپت وضعیت USB dongle و middleware را بررسی می‌کند
"""

import os
import sys
import django
from datetime import datetime, timedelta

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from usb_key_validator.enhanced_utils import dongle_manager
from django.core.cache import cache

User = get_user_model()

def check_usb_dongle_status():
    """بررسی وضعیت USB dongle"""
    
    print("🔍 بررسی وضعیت USB dongle و middleware")
    print("=" * 60)
    
    # بررسی USB drives
    print("📱 بررسی USB drives:")
    usb_drives = dongle_manager.find_usb_drives()
    if usb_drives:
        print(f"   ✅ {len(usb_drives)} USB drive یافت شد:")
        for drive in usb_drives:
            print(f"      - {drive['device_id']}: {drive['size']} GB")
    else:
        print("   ❌ هیچ USB drive یافت نشد")
    
    # بررسی اعتبارسنجی روزانه
    print(f"\n🔐 بررسی اعتبارسنجی روزانه:")
    try:
        result = dongle_manager.daily_validation_check()
        print(f"   - وضعیت: {'✅ معتبر' if result['valid'] else '❌ نامعتبر'}")
        print(f"   - پیام: {result['message']}")
        print(f"   - جزئیات: {result.get('details', 'ندارد')}")
    except Exception as e:
        print(f"   ❌ خطا در اعتبارسنجی: {e}")
    
    # بررسی cache
    print(f"\n💾 بررسی cache:")
    try:
        # بررسی cache برای کاربر admin
        admin_user = User.objects.get(username='admin')
        cache_key = f'usb_validation_{admin_user.id}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"   ✅ Cache موجود: {cached_result}")
        else:
            print(f"   ℹ️ هیچ cache موجود نیست")
    except Exception as e:
        print(f"   ❌ خطا در بررسی cache: {e}")
    
    # بررسی middleware settings
    print(f"\n⚙️ بررسی تنظیمات middleware:")
    from django.conf import settings
    middleware_list = getattr(settings, 'MIDDLEWARE', [])
    
    usb_middleware_found = False
    for middleware in middleware_list:
        if 'USBDongleValidationMiddleware' in middleware:
            usb_middleware_found = True
            print(f"   ✅ Middleware فعال: {middleware}")
            break
    
    if not usb_middleware_found:
        print(f"   ❌ Middleware USB dongle یافت نشد")
    
    # بررسی exempt URLs
    print(f"\n🚫 بررسی URL های معاف:")
    exempt_urls = [
        '/admin/login/',
        '/accounts/login/',
        '/usb-key-validator/',
        '/usb-key-validator/enhanced/',
        '/usb-key-validator/dashboard/',
        '/favicon.ico',
        '/static/',
        '/media/',
    ]
    
    for url in exempt_urls:
        print(f"   - {url}")
    
    # تست اعتبارسنجی برای کاربر admin
    print(f"\n👤 تست اعتبارسنجی برای کاربر admin:")
    try:
        admin_user = User.objects.get(username='admin')
        print(f"   - کاربر: {admin_user.username}")
        print(f"   - Superuser: {'✅ بله' if admin_user.is_superuser else '❌ خیر'}")
        print(f"   - فعال: {'✅ بله' if admin_user.is_active else '❌ خیر'}")
        
        if admin_user.is_superuser:
            print(f"   ℹ️ کاربر superuser است - معاف از اعتبارسنجی middleware")
        else:
            print(f"   ⚠️ کاربر superuser نیست - نیاز به اعتبارسنجی")
            
    except User.DoesNotExist:
        print(f"   ❌ کاربر admin یافت نشد")

def test_middleware_behavior():
    """تست رفتار middleware"""
    
    print(f"\n🧪 تست رفتار middleware:")
    print(f"=" * 40)
    
    # شبیه‌سازی درخواست
    test_urls = [
        '/admin/',
        '/usb-key-validator/enhanced/',
        '/usb-key-validator/dashboard/',
        '/accounts/profile/',
    ]
    
    for url in test_urls:
        print(f"\n📄 تست URL: {url}")
        
        # بررسی exempt URLs
        exempt_urls = [
            '/admin/login/',
            '/accounts/login/',
            '/usb-key-validator/',
            '/usb-key-validator/enhanced/',
            '/usb-key-validator/dashboard/',
            '/favicon.ico',
            '/static/',
            '/media/',
        ]
        
        is_exempt = any(url.startswith(exempt_url) for exempt_url in exempt_urls)
        print(f"   - معاف از اعتبارسنجی: {'✅ بله' if is_exempt else '❌ خیر'}")
        
        if not is_exempt:
            print(f"   - نیاز به اعتبارسنجی USB dongle")
        else:
            print(f"   - معاف از اعتبارسنجی")

def clear_usb_validation_cache():
    """پاک کردن cache اعتبارسنجی USB"""
    
    print(f"\n🧹 پاک کردن cache اعتبارسنجی USB:")
    
    try:
        admin_user = User.objects.get(username='admin')
        cache_key = f'usb_validation_{admin_user.id}'
        cache.delete(cache_key)
        print(f"   ✅ Cache پاک شد: {cache_key}")
    except Exception as e:
        print(f"   ❌ خطا در پاک کردن cache: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='بررسی وضعیت USB dongle و middleware')
    parser.add_argument('--clear-cache', action='store_true', help='پاک کردن cache اعتبارسنجی')
    parser.add_argument('--test-middleware', action='store_true', help='تست رفتار middleware')
    
    args = parser.parse_args()
    
    if args.clear_cache:
        clear_usb_validation_cache()
    elif args.test_middleware:
        test_middleware_behavior()
    else:
        check_usb_dongle_status()
        test_middleware_behavior()
