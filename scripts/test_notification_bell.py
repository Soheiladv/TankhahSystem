#!/usr/bin/env python
"""
اسکریپت تست زنگوله اعلان‌ها
این اسکریپت اعلان‌های تستی ایجاد می‌کند تا عملکرد زنگوله را بررسی کنیم
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
from notificationApp.models import Notification, NotificationRule
from django.utils import timezone

User = get_user_model()

def create_test_notifications():
    """ایجاد اعلان‌های تستی برای بررسی عملکرد زنگوله"""
    
    print("🔔 شروع تست زنگوله اعلان‌ها...")
    
    # دریافت کاربر admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # حذف اعلان‌های قدیمی تست
    old_notifications = Notification.objects.filter(
        recipient=admin_user,
        description__icontains='تست زنگوله'
    )
    deleted_count = old_notifications.count()
    old_notifications.delete()
    if deleted_count > 0:
        print(f"🗑️ {deleted_count} اعلان قدیمی حذف شد")
    
    # ایجاد اعلان‌های تستی
    test_notifications = [
        {
            'actor': admin_user,  # استفاده از کاربر admin به عنوان actor
            'verb': 'اعلان تستی ایجاد کرد',
            'description': 'تست زنگوله - اعلان شماره 1',
            'entity_type': 'system',
            'priority': 'high'
        },
        {
            'actor': admin_user,  # استفاده از کاربر admin به عنوان actor
            'verb': 'عملیات تستی انجام داد',
            'description': 'تست زنگوله - اعلان شماره 2',
            'entity_type': 'user',
            'priority': 'medium'
        },
        {
            'actor': admin_user,  # استفاده از کاربر admin به عنوان actor
            'verb': 'اعلان مهم ارسال کرد',
            'description': 'تست زنگوله - اعلان شماره 3 (مهم)',
            'entity_type': 'system',
            'priority': 'high'
        }
    ]
    
    created_notifications = []
    for i, notif_data in enumerate(test_notifications, 1):
        notification = Notification.objects.create(
            recipient=admin_user,
            actor=notif_data['actor'],
            verb=notif_data['verb'],
            description=notif_data['description'],
            entity_type=notif_data['entity_type'],
            priority=notif_data['priority'],
            timestamp=timezone.now() + timedelta(seconds=i)  # تاخیر کمی برای هر اعلان
        )
        created_notifications.append(notification)
        print(f"✅ اعلان {i} ایجاد شد: {notif_data['description']}")
    
    # نمایش آمار
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"\n📊 آمار اعلان‌ها:")
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
    print(f"   - اعلان‌های تستی ایجاد شده: {len(created_notifications)}")
    
    print(f"\n🎯 دستورالعمل تست:")
    print(f"   1. به پنل ادمین بروید: http://127.0.0.1:8000/admin/")
    print(f"   2. زنگوله در نوار بالایی باید {unread_notifications} اعلان نشان دهد")
    print(f"   3. زنگوله باید انیمیشن لرزش و pulse داشته باشد")
    print(f"   4. روی زنگوله کلیک کنید تا اعلان‌ها را ببینید")
    
    return created_notifications

def test_notification_animations():
    """تست انیمیشن‌های زنگوله"""
    
    print(f"\n🎬 تست انیمیشن‌های زنگوله:")
    print(f"   - انیمیشن shake: لرزش زنگوله هنگام اعلان جدید")
    print(f"   - انیمیشن pulse: ضربان مداوم زنگوله")
    print(f"   - انیمیشن bounce: جهش badge شمارنده")
    print(f"   - انیمیشن fade: محو شدن اعلان‌ها")
    
    print(f"\n🔧 کلاس‌های CSS فعال:")
    print(f"   - .notification-bell.shake")
    print(f"   - .notification-bell.pulse") 
    print(f"   - .notification-badge.animate")
    print(f"   - .notification-item.unread")

def cleanup_test_notifications():
    """پاکسازی اعلان‌های تستی"""
    
    print(f"\n🧹 پاکسازی اعلان‌های تستی...")
    
    try:
        admin_user = User.objects.get(username='admin')
        test_notifications = Notification.objects.filter(
            recipient=admin_user,
            description__icontains='تست زنگوله'
        )
        deleted_count = test_notifications.count()
        test_notifications.delete()
        print(f"✅ {deleted_count} اعلان تستی حذف شد")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تست زنگوله اعلان‌ها')
    parser.add_argument('--cleanup', action='store_true', help='پاکسازی اعلان‌های تستی')
    parser.add_argument('--animations', action='store_true', help='نمایش اطلاعات انیمیشن‌ها')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_notifications()
    elif args.animations:
        test_notification_animations()
    else:
        create_test_notifications()
        test_notification_animations()
