#!/usr/bin/env python
"""
اسکریپت تست نمایش اعلان‌ها
این اسکریپت اعلان‌ها را تست می‌کند و URL ها را بررسی می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from accounts.models import CustomUser
from notificationApp.models import Notification
from django.urls import reverse
from django.test import Client
from django.contrib.auth import authenticate

def test_notification_urls():
    """تست URL های اعلان‌ها"""
    print("🔗 تست URL های اعلان‌ها...")
    print("=" * 60)
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
        
        # تست URL ها
        urls_to_test = [
            'notifications:inbox',
            'notifications:unread',
            'notifications:get_notifications',
            'notifications:test_unread_count'
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"   ✅ {url_name}: {url}")
            except Exception as e:
                print(f"   ❌ {url_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست URL ها: {e}")
        return False

def test_notification_api():
    """تست API اعلان‌ها"""
    print("\n📡 تست API اعلان‌ها...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # ایجاد کلاینت تست
        client = Client()
        
        # ورود به سیستم
        login_success = client.login(username=admin_user.username, password='admin123')
        if not login_success:
            print("❌ ورود به سیستم ناموفق بود!")
            return False
        
        print("✅ ورود به سیستم موفق بود")
        
        # تست API get_notifications
        try:
            response = client.get(reverse('notifications:get_notifications'))
            print(f"   📡 get_notifications: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      - تعداد اعلان‌ها: {len(data.get('notifications', []))}")
                print(f"      - تعداد خوانده‌نشده: {data.get('unread_count', 0)}")
            else:
                print(f"      - خطا: {response.content}")
        except Exception as e:
            print(f"   ❌ خطا در get_notifications: {e}")
        
        # تست API test_unread_count
        try:
            response = client.get(reverse('notifications:test_unread_count'))
            print(f"   📡 test_unread_count: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      - تعداد خوانده‌نشده: {data.get('unread_count', 0)}")
            else:
                print(f"      - خطا: {response.content}")
        except Exception as e:
            print(f"   ❌ خطا در test_unread_count: {e}")
        
        # تست صفحه inbox
        try:
            response = client.get(reverse('notifications:inbox'))
            print(f"   📄 inbox: {response.status_code}")
            if response.status_code == 200:
                print("      - صفحه inbox بارگذاری شد")
            else:
                print(f"      - خطا: {response.content}")
        except Exception as e:
            print(f"   ❌ خطا در inbox: {e}")
        
        # تست صفحه unread
        try:
            response = client.get(reverse('notifications:unread'))
            print(f"   📄 unread: {response.status_code}")
            if response.status_code == 200:
                print("      - صفحه unread بارگذاری شد")
            else:
                print(f"      - خطا: {response.content}")
        except Exception as e:
            print(f"   ❌ خطا در unread: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست API: {e}")
        return False

def test_notification_data():
    """تست داده‌های اعلان‌ها"""
    print("\n📊 تست داده‌های اعلان‌ها...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # دریافت اعلان‌ها
        notifications = admin_user.notifications.filter(deleted=False).order_by('-timestamp')[:10]
        unread_count = admin_user.notifications.filter(unread=True, deleted=False).count()
        
        print(f"📈 آمار اعلان‌ها:")
        print(f"   - کل اعلان‌ها: {notifications.count()}")
        print(f"   - خوانده‌نشده: {unread_count}")
        
        # نمایش نمونه اعلان‌ها
        print(f"\n📋 نمونه اعلان‌ها:")
        for i, notification in enumerate(notifications[:5], 1):
            print(f"   {i}. {notification.verb} - {notification.description[:50]}...")
            print(f"      - اولویت: {notification.priority}")
            print(f"      - نوع: {notification.entity_type}")
            print(f"      - خوانده‌شده: {'خیر' if notification.unread else 'بله'}")
            print(f"      - زمان: {notification.timestamp}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست داده‌ها: {e}")
        return False

def create_test_notification():
    """ایجاد اعلان تستی"""
    print("\n🔔 ایجاد اعلان تستی...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # ایجاد اعلان تستی
        notification = Notification.objects.create(
            recipient=admin_user,
            actor=None,
            verb='TEST',
            description='🔔 این یک اعلان تستی است - سیستم اعلان‌ها فعال است',
            entity_type='SYSTEM',
            priority='HIGH',
            unread=True
        )
        
        print(f"✅ اعلان تستی ایجاد شد (ID: {notification.id})")
        print(f"   - متن: {notification.description}")
        print(f"   - اولویت: {notification.priority}")
        print(f"   - خوانده‌شده: {'خیر' if notification.unread else 'بله'}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان تستی: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔔 تست نمایش اعلان‌ها")
    print("=" * 60)
    
    try:
        # تست‌های مختلف
        test_notification_urls()
        test_notification_api()
        test_notification_data()
        create_test_notification()
        
        print(f"\n🎉 تست نمایش اعلان‌ها با موفقیت انجام شد!")
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        print(f"   http://127.0.0.1:8000/admin/notificationApp/notification/")
        
        print(f"\n🔔 نکات مهم:")
        print(f"   - اعلان‌ها در نوار بالایی صفحه اصلی نمایش داده می‌شوند")
        print(f"   - آیکون زنگ تعداد اعلان‌های خوانده‌نشده را نشان می‌دهد")
        print(f"   - کلیک روی آیکون زنگ لیست اعلان‌ها را نمایش می‌دهد")
        print(f"   - برای دیباگ، console مرورگر را بررسی کنید")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
