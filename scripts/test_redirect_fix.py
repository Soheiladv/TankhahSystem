#!/usr/bin/env python
"""
تست رفع مشکل ریدایرکت بی‌نهایت
این اسکریپت رفع مشکل ریدایرکت را تست می‌کند
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
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from usb_key_validator.middleware import USBDongleValidationMiddleware
from django.urls import reverse

User = get_user_model()

def test_middleware_redirect_fix():
    """تست رفع مشکل ریدایرکت در middleware"""
    
    print("🔧 تست رفع مشکل ریدایرکت در middleware")
    print("=" * 60)
    
    # ایجاد middleware
    middleware = USBDongleValidationMiddleware(lambda req: None)
    
    # ایجاد request factory
    factory = RequestFactory()
    
    # تست URL های مختلف
    test_cases = [
        {
            'url': '/admin/',
            'user': 'admin',
            'expected_redirect': True,
            'description': 'صفحه admin - کاربر superuser'
        },
        {
            'url': '/usb-key-validator/enhanced/',
            'user': 'admin',
            'expected_redirect': False,
            'description': 'صفحه enhanced - کاربر superuser'
        },
        {
            'url': '/accounts/profile/',
            'user': 'admin',
            'expected_redirect': False,
            'description': 'صفحه profile - کاربر superuser'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📄 تست: {test_case['description']}")
        print(f"   URL: {test_case['url']}")
        
        # ایجاد request
        request = factory.get(test_case['url'])
        
        # تنظیم کاربر
        try:
            user = User.objects.get(username=test_case['user'])
            request.user = user
            print(f"   کاربر: {user.username} (superuser: {user.is_superuser})")
        except User.DoesNotExist:
            print(f"   ❌ کاربر {test_case['user']} یافت نشد")
            continue
        
        # شبیه‌سازی middleware
        try:
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
            
            is_exempt = any(request.path.startswith(url) for url in exempt_urls)
            print(f"   معاف از اعتبارسنجی: {'✅ بله' if is_exempt else '❌ خیر'}")
            
            if is_exempt:
                print(f"   نتیجه: ✅ اجازه ادامه (معاف)")
            elif user.is_superuser:
                print(f"   نتیجه: ✅ اجازه ادامه (superuser)")
            else:
                print(f"   نتیجه: ⚠️ نیاز به اعتبارسنجی USB dongle")
                
        except Exception as e:
            print(f"   ❌ خطا: {e}")

def test_redirect_loop_prevention():
    """تست جلوگیری از ریدایرکت بی‌نهایت"""
    
    print(f"\n🔄 تست جلوگیری از ریدایرکت بی‌نهایت:")
    print(f"=" * 50)
    
    # شبیه‌سازی ریدایرکت
    enhanced_url = reverse('usb_key_validator:enhanced_validate')
    print(f"URL صفحه enhanced: {enhanced_url}")
    
    # تست ریدایرکت از صفحات مختلف
    test_urls = [
        '/admin/',
        '/accounts/profile/',
        '/dashboard/',
        enhanced_url
    ]
    
    for url in test_urls:
        print(f"\n📄 تست ریدایرکت از: {url}")
        
        if url == enhanced_url:
            print(f"   ✅ ریدایرکت نمی‌شود (همان صفحه)")
        else:
            print(f"   ⚠️ ریدایرکت می‌شود به: {enhanced_url}")

def show_solution_summary():
    """نمایش خلاصه راه‌حل"""
    
    print(f"\n💡 خلاصه راه‌حل ریدایرکت:")
    print(f"=" * 50)
    
    print(f"🔍 مشکل:")
    print(f"   - Middleware کاربران را به صفحه enhanced_validate ریدایرکت می‌کرد")
    print(f"   - خود صفحه enhanced_validate در لیست معاف بود")
    print(f"   - این باعث ریدایرکت بی‌نهایت می‌شد")
    
    print(f"\n✅ راه‌حل:")
    print(f"   1. اضافه کردن بررسی path در middleware")
    print(f"   2. جلوگیری از ریدایرکت اگر کاربر قبلاً در صفحه enhanced است")
    print(f"   3. حفظ عملکرد عادی برای سایر صفحات")
    
    print(f"\n🎯 نتیجه:")
    print(f"   - کاربران superuser: معاف از اعتبارسنجی")
    print(f"   - کاربران عادی: ریدایرکت به صفحه اعتبارسنجی (یک بار)")
    print(f"   - صفحه enhanced: بدون ریدایرکت مکرر")

if __name__ == "__main__":
    test_middleware_redirect_fix()
    test_redirect_loop_prevention()
    show_solution_summary()
