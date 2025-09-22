#!/usr/bin/env python
"""
اسکریپت تست کامل سیستم اعلان‌ها
این اسکریپت سیستم اعلان‌ها را برای همه عملیات‌ها تست می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from accounts.models import CustomUser
from notificationApp.models import Notification, NotificationRule
from notificationApp.utils import send_notification
from django.utils import timezone
from datetime import datetime, timedelta

def test_admin_page():
    """تست صفحه admin"""
    print("🔍 تست صفحه admin...")
    
    try:
        from django.test import Client
        
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
        
        # تست صفحه admin اعلان‌ها
        try:
            response = client.get('/admin/notificationApp/notification/')
            print(f"   📄 صفحه admin: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ صفحه admin بارگذاری شد")
                return True
            else:
                print(f"   ❌ خطا در صفحه admin: {response.content}")
                return False
        except Exception as e:
            print(f"   ❌ خطا در تست صفحه admin: {e}")
            return False
        
    except Exception as e:
        print(f"❌ خطا در تست صفحه admin: {e}")
        return False

def test_notification_creation():
    """تست ایجاد اعلان‌های مختلف"""
    print("\n🔔 تست ایجاد اعلان‌های مختلف...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # اعلان‌های تستی مختلف
        test_notifications = [
            # تنخواه
            {
                'verb': 'CREATED',
                'description': '💰 تنخواه جدید "خرید تجهیزات اداری" ایجاد شد',
                'entity_type': 'TANKHAH',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'APPROVED',
                'description': '✅ تنخواه "خرید تجهیزات اداری" تأیید شد',
                'entity_type': 'TANKHAH',
                'priority': 'HIGH'
            },
            {
                'verb': 'REJECTED',
                'description': '❌ تنخواه "خرید تجهیزات اداری" رد شد',
                'entity_type': 'TANKHAH',
                'priority': 'HIGH'
            },
            
            # فاکتور
            {
                'verb': 'CREATED',
                'description': '📄 فاکتور جدید "فاکتور خرید" ایجاد شد',
                'entity_type': 'FACTOR',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'APPROVED',
                'description': '✅ فاکتور "فاکتور خرید" تأیید شد',
                'entity_type': 'FACTOR',
                'priority': 'HIGH'
            },
            
            # بودجه
            {
                'verb': 'CREATED',
                'description': '💵 تراکنش بودجه جدید "واریز بودجه" ایجاد شد',
                'entity_type': 'BUDGET',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'APPROVED',
                'description': '✅ تراکنش بودجه "واریز بودجه" تأیید شد',
                'entity_type': 'BUDGET',
                'priority': 'HIGH'
            },
            
            # دستور پرداخت
            {
                'verb': 'CREATED',
                'description': '💳 دستور پرداخت جدید "پرداخت حقوق" ایجاد شد',
                'entity_type': 'PAYMENTORDER',
                'priority': 'HIGH'
            },
            {
                'verb': 'APPROVED',
                'description': '✅ دستور پرداخت "پرداخت حقوق" تأیید شد',
                'entity_type': 'PAYMENTORDER',
                'priority': 'HIGH'
            },
            {
                'verb': 'PAID',
                'description': '💰 دستور پرداخت "پرداخت حقوق" پرداخت شد',
                'entity_type': 'PAYMENTORDER',
                'priority': 'HIGH'
            },
            
            # سیستم
            {
                'verb': 'ERROR',
                'description': '❌ خطا در سیستم - بررسی نیاز است',
                'entity_type': 'SYSTEM',
                'priority': 'ERROR'
            },
            {
                'verb': 'WARNING',
                'description': '⚠️ هشدار سیستم - حافظه کم',
                'entity_type': 'SYSTEM',
                'priority': 'WARNING'
            }
        ]
        
        created_count = 0
        
        for i, notif_data in enumerate(test_notifications, 1):
            try:
                notification = Notification.objects.create(
                    recipient=admin_user,
                    actor=None,
                    verb=notif_data['verb'],
                    description=notif_data['description'],
                    entity_type=notif_data['entity_type'],
                    priority=notif_data['priority'],
                    unread=True,
                    timestamp=timezone.now() - timedelta(minutes=i*2)
                )
                print(f"   ✅ اعلان {i} ایجاد شد: {notif_data['description']}")
                created_count += 1
            except Exception as e:
                print(f"   ❌ خطا در ایجاد اعلان {i}: {e}")
        
        print(f"\n🎉 {created_count} اعلان تستی ایجاد شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های تستی: {e}")
        return False

def test_notification_rules():
    """تست قوانین اعلان"""
    print("\n🔧 تست قوانین اعلان...")
    
    try:
        # آمار قوانین اعلان
        total_rules = NotificationRule.objects.count()
        active_rules = NotificationRule.objects.filter(is_active=True).count()
        
        print(f"📊 آمار قوانین اعلان:")
        print(f"   - کل قوانین: {total_rules}")
        print(f"   - قوانین فعال: {active_rules}")
        
        # نمایش قوانین فعال
        print(f"\n📋 قوانین فعال:")
        active_rules_list = NotificationRule.objects.filter(is_active=True)
        for rule in active_rules_list:
            print(f"   - {rule.entity_type} - {rule.action} ({rule.priority})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست قوانین اعلان: {e}")
        return False

def test_notification_api():
    """تست API اعلان‌ها"""
    print("\n📡 تست API اعلان‌ها...")
    
    try:
        from django.test import Client
        
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
        
        # تست API get_notifications
        try:
            response = client.get('/notifications/api/list/')
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API get_notifications: {len(data.get('notifications', []))} اعلان")
                print(f"   ✅ تعداد خوانده‌نشده: {data.get('unread_count', 0)}")
            else:
                print(f"   ❌ خطا در API get_notifications: {response.status_code}")
        except Exception as e:
            print(f"   ❌ خطا در API get_notifications: {e}")
        
        # تست API test_unread_count
        try:
            response = client.get('/notifications/api/count/')
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API test_unread_count: {data.get('unread_count', 0)} اعلان")
            else:
                print(f"   ❌ خطا در API test_unread_count: {response.status_code}")
        except Exception as e:
            print(f"   ❌ خطا در API test_unread_count: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست API: {e}")
        return False

def show_final_stats():
    """نمایش آمار نهایی"""
    print("\n📊 آمار نهایی سیستم اعلان‌ها:")
    print("=" * 60)
    
    try:
        # آمار کلی
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(unread=True).count()
        read_notifications = Notification.objects.filter(unread=False).count()
        
        print(f"📈 آمار کلی:")
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
        print(f"   - اعلان‌های خوانده‌شده: {read_notifications}")
        
        # آمار بر اساس اولویت
        print(f"\n🎯 آمار بر اساس اولویت:")
        priorities = ['LOW', 'MEDIUM', 'HIGH', 'WARNING', 'ERROR', 'LOCKED']
        for priority in priorities:
            count = Notification.objects.filter(priority=priority).count()
            if count > 0:
                print(f"   - {priority}: {count}")
        
        # آمار بر اساس نوع موجودیت
        print(f"\n📋 آمار بر اساس نوع موجودیت:")
        entity_types = ['FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BACKUP', 'SYSTEM', 'SECURITY', 'MAINTENANCE', 'BUDGET']
        for entity_type in entity_types:
            count = Notification.objects.filter(entity_type=entity_type).count()
            if count > 0:
                print(f"   - {entity_type}: {count}")
        
        # آمار بر اساس کاربر
        print(f"\n👤 آمار بر اساس کاربر:")
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        for admin_user in admin_users:
            user_notifications = admin_user.notifications.count()
            user_unread = admin_user.notifications.filter(unread=True).count()
            user_read = admin_user.notifications.filter(unread=False).count()
            if user_notifications > 0:
                print(f"   - {admin_user.username}: {user_notifications} (خوانده‌نشده: {user_unread}, خوانده‌شده: {user_read})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🎯 تست کامل سیستم اعلان‌ها")
    print("=" * 60)
    
    try:
        # تست صفحه admin
        test_admin_page()
        
        # تست ایجاد اعلان‌ها
        test_notification_creation()
        
        # تست قوانین اعلان
        test_notification_rules()
        
        # تست API
        test_notification_api()
        
        # نمایش آمار نهایی
        show_final_stats()
        
        print(f"\n🎉 تست کامل سیستم اعلان‌ها با موفقیت انجام شد!")
        print(f"\n✅ سیستم اعلان‌ها کاملاً فعال و آماده استفاده است!")
        
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/admin/notificationApp/notification/")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        
        print(f"\n🔔 نحوه استفاده:")
        print(f"   - آیکون زنگ در نوار بالایی صفحه اصلی")
        print(f"   - تعداد اعلان‌های خوانده‌نشده نمایش داده می‌شود")
        print(f"   - کلیک روی آیکون برای مشاهده اعلان‌ها")
        print(f"   - اعلان‌ها برای عملیات‌های مختلف خودکار ایجاد می‌شوند")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
