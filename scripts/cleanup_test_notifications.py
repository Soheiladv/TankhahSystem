#!/usr/bin/env python
"""
پاکسازی اعلان‌های تستی
این اسکریپت اعلان‌های تستی را پاک می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notificationApp.models import Notification
from django.utils import timezone

User = get_user_model()

def cleanup_test_notifications():
    """پاکسازی اعلان‌های تستی"""
    
    print("🧹 پاکسازی اعلان‌های تستی")
    print("=" * 40)
    
    # دریافت کاربر admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # حذف اعلان‌های تستی
    test_notifications = Notification.objects.filter(
        recipient=admin_user,
        description__icontains='تست'
    )
    
    deleted_count = test_notifications.count()
    if deleted_count > 0:
        test_notifications.delete()
        print(f"✅ {deleted_count} اعلان تستی حذف شد")
    else:
        print("ℹ️ هیچ اعلان تستی یافت نشد")
    
    # نمایش آمار نهایی
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"\n📊 آمار نهایی:")
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")

if __name__ == "__main__":
    cleanup_test_notifications()
