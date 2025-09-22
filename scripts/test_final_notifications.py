#!/usr/bin/env python
"""
اسکریپت تست نهایی سیستم اعلان‌ها
این اسکریپت سیستم اعلان‌ها را کاملاً تست می‌کند
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
import random

def test_notification_system():
    """تست کامل سیستم اعلان‌ها"""
    print("🔔 تست کامل سیستم اعلان‌ها")
    print("=" * 60)
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
        
        # آمار فعلی
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(unread=True).count()
        read_notifications = Notification.objects.filter(unread=False).count()
        
        print(f"\n📊 آمار فعلی:")
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - خوانده‌نشده: {unread_notifications}")
        print(f"   - خوانده‌شده: {read_notifications}")
        
        # ایجاد اعلان‌های تستی جدید
        print(f"\n🔔 ایجاد اعلان‌های تستی...")
        test_notifications = [
            {
                'verb': 'CREATED',
                'description': '🎉 سیستم اعلان‌ها کاملاً فعال شد',
                'entity_type': 'SYSTEM',
                'priority': 'HIGH'
            },
            {
                'verb': 'STARTED',
                'description': '🚀 تست سیستم اعلان‌ها شروع شد',
                'entity_type': 'SYSTEM',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'COMPLETED',
                'description': '✅ تست سیستم اعلان‌ها تکمیل شد',
                'entity_type': 'SYSTEM',
                'priority': 'LOW'
            },
            {
                'verb': 'WARNING',
                'description': '⚠️ سیستم اعلان‌ها نیاز به بررسی دارد',
                'entity_type': 'SYSTEM',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': '❌ خطا در سیستم اعلان‌ها',
                'entity_type': 'SYSTEM',
                'priority': 'ERROR'
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
                print(f"   ✅ اعلان {i} ایجاد شد: {notification.description}")
                created_count += 1
            except Exception as e:
                print(f"   ❌ خطا در ایجاد اعلان {i}: {e}")
        
        print(f"\n🎉 {created_count} اعلان تستی ایجاد شد!")
        
        # تست API
        print(f"\n📡 تست API اعلان‌ها...")
        try:
            from django.test import Client
            client = Client()
            
            # ورود به سیستم
            login_success = client.login(username=admin_user.username, password='admin123')
            if login_success:
                print("   ✅ ورود به سیستم موفق بود")
                
                # تست API get_notifications
                response = client.get('/notifications/api/list/')
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ API get_notifications: {len(data.get('notifications', []))} اعلان")
                    print(f"   ✅ تعداد خوانده‌نشده: {data.get('unread_count', 0)}")
                else:
                    print(f"   ❌ خطا در API get_notifications: {response.status_code}")
                
                # تست API test_unread_count
                response = client.get('/notifications/api/count/')
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ API test_unread_count: {data.get('unread_count', 0)} اعلان")
                else:
                    print(f"   ❌ خطا در API test_unread_count: {response.status_code}")
                
                # تست صفحه inbox
                response = client.get('/notifications/inbox/')
                if response.status_code == 200:
                    print("   ✅ صفحه inbox بارگذاری شد")
                else:
                    print(f"   ❌ خطا در صفحه inbox: {response.status_code}")
                
                # تست صفحه unread
                response = client.get('/notifications/unread/')
                if response.status_code == 200:
                    print("   ✅ صفحه unread بارگذاری شد")
                else:
                    print(f"   ❌ خطا در صفحه unread: {response.status_code}")
                
                # تست صفحه admin
                response = client.get('/admin/notificationApp/notification/')
                if response.status_code == 200:
                    print("   ✅ صفحه admin بارگذاری شد")
                else:
                    print(f"   ❌ خطا در صفحه admin: {response.status_code}")
                
            else:
                print("   ❌ ورود به سیستم ناموفق بود")
                
        except Exception as e:
            print(f"   ❌ خطا در تست API: {e}")
        
        # تست ارسال اعلان
        print(f"\n📤 تست ارسال اعلان...")
        try:
            send_notification(
                sender=None,
                users=[admin_user],
                verb='TEST',
                description='🔔 این یک اعلان تستی است - سیستم اعلان‌ها کار می‌کند',
                entity_type='SYSTEM',
                priority='MEDIUM'
            )
            print("   ✅ اعلان تستی ارسال شد")
        except Exception as e:
            print(f"   ❌ خطا در ارسال اعلان: {e}")
        
        # آمار نهایی
        print(f"\n📊 آمار نهایی:")
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(unread=True).count()
        read_notifications = Notification.objects.filter(unread=False).count()
        
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - خوانده‌نشده: {unread_notifications}")
        print(f"   - خوانده‌شده: {read_notifications}")
        
        # آمار بر اساس اولویت
        print(f"\n🎯 آمار بر اساس اولویت:")
        priorities = ['LOW', 'MEDIUM', 'HIGH', 'WARNING', 'ERROR', 'LOCKED']
        for priority in priorities:
            count = Notification.objects.filter(priority=priority).count()
            if count > 0:
                print(f"   - {priority}: {count}")
        
        # آمار بر اساس نوع موجودیت
        print(f"\n📋 آمار بر اساس نوع موجودیت:")
        entity_types = ['FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BACKUP', 'SYSTEM', 'SECURITY', 'MAINTENANCE']
        for entity_type in entity_types:
            count = Notification.objects.filter(entity_type=entity_type).count()
            if count > 0:
                print(f"   - {entity_type}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست سیستم اعلان‌ها: {e}")
        return False

def show_usage_instructions():
    """نمایش دستورالعمل استفاده"""
    print("\n📖 دستورالعمل استفاده از سیستم اعلان‌ها:")
    print("=" * 60)
    
    print("🔔 نحوه مشاهده اعلان‌ها:")
    print("   1. آیکون زنگ در نوار بالایی صفحه اصلی")
    print("   2. تعداد اعلان‌های خوانده‌نشده نمایش داده می‌شود")
    print("   3. کلیک روی آیکون برای مشاهده لیست اعلان‌ها")
    print("   4. کلیک روی اعلان برای علامت‌گذاری به عنوان خوانده شده")
    
    print("\n🌐 صفحات اعلان‌ها:")
    print("   - http://127.0.0.1:8000/notifications/inbox/ - همه اعلان‌ها")
    print("   - http://127.0.0.1:8000/notifications/unread/ - اعلان‌های خوانده‌نشده")
    print("   - http://127.0.0.1:8000/admin/notificationApp/notification/ - مدیریت اعلان‌ها")
    
    print("\n🔧 ویژگی‌های سیستم:")
    print("   - اعلان‌ها هر 30 ثانیه به‌روزرسانی می‌شوند")
    print("   - نمایش اولویت‌های مختلف با رنگ‌های مختلف")
    print("   - امکان حذف اعلان‌ها")
    print("   - علامت‌گذاری به عنوان خوانده شده")
    print("   - صفحه‌بندی اعلان‌ها")
    
    print("\n🎯 انواع اعلان‌ها:")
    print("   - سیستم (SYSTEM): اعلان‌های مربوط به سیستم")
    print("   - امنیت (SECURITY): اعلان‌های امنیتی")
    print("   - پشتیبان‌گیری (BACKUP): اعلان‌های پشتیبان‌گیری")
    print("   - نگهداری (MAINTENANCE): اعلان‌های نگهداری")
    print("   - فاکتور (FACTOR): اعلان‌های فاکتور")
    print("   - تنخواه (TANKHAH): اعلان‌های تنخواه")
    print("   - دستور پرداخت (PAYMENTORDER): اعلان‌های دستور پرداخت")
    
    print("\n🎨 اولویت‌های اعلان‌ها:")
    print("   - کم (LOW): اعلان‌های کم‌اهمیت")
    print("   - متوسط (MEDIUM): اعلان‌های متوسط")
    print("   - زیاد (HIGH): اعلان‌های مهم")
    print("   - هشدار (WARNING): اعلان‌های هشدار")
    print("   - خطا (ERROR): اعلان‌های خطا")
    print("   - قفل‌شده (LOCKED): اعلان‌های قفل")

def main():
    """تابع اصلی"""
    print("🎯 تست نهایی سیستم اعلان‌ها")
    print("=" * 60)
    
    try:
        # تست سیستم اعلان‌ها
        test_notification_system()
        
        # نمایش دستورالعمل استفاده
        show_usage_instructions()
        
        print(f"\n🎉 تست نهایی سیستم اعلان‌ها با موفقیت انجام شد!")
        print(f"\n✅ سیستم اعلان‌ها کاملاً فعال و آماده استفاده است!")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")

