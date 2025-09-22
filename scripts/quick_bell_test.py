#!/usr/bin/env python
"""
تست سریع زنگوله اعلان‌ها
این اسکریپت یک اعلان تستی ایجاد می‌کند تا زنگوله را تست کنیم
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
from notificationApp.models import Notification
from django.utils import timezone

User = get_user_model()

def create_quick_test_notification():
    """ایجاد یک اعلان تستی سریع"""
    
    print("🔔 تست سریع زنگوله اعلان‌ها")
    print("=" * 40)
    
    # دریافت کاربر admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # ایجاد اعلان تستی
    notification = Notification.objects.create(
        recipient=admin_user,
        actor=admin_user,
        verb='تست زنگوله انجام داد',
        description='تست سریع زنگوله - ' + timezone.now().strftime('%H:%M:%S'),
        entity_type='system',
        priority='high',
        timestamp=timezone.now()
    )
    
    print(f"✅ اعلان تستی ایجاد شد: {notification.description}")
    
    # نمایش آمار
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"\n📊 آمار اعلان‌ها:")
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
    
    print(f"\n🎯 برای مشاهده زنگوله:")
    print(f"   1. به پنل ادمین بروید: http://127.0.0.1:8000/admin/")
    print(f"   2. زنگوله باید {unread_notifications} اعلان نشان دهد")
    print(f"   3. انیمیشن‌های shake و pulse باید فعال باشند")
    print(f"   4. روی زنگوله کلیک کنید تا اعلان‌ها را ببینید")
    
    return notification

if __name__ == "__main__":
    create_quick_test_notification()
