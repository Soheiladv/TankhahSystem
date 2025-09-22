#!/usr/bin/env python
"""
تست نهایی سیستم اعلان‌ها
این اسکریپت تمام جنبه‌های سیستم اعلان‌ها را تست می‌کند
"""

import os
import sys
import django
import time
from datetime import datetime, timedelta

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notificationApp.models import Notification, NotificationRule
from django.utils import timezone

User = get_user_model()

def test_complete_notification_system():
    """تست کامل سیستم اعلان‌ها"""
    
    print("🔔 تست کامل سیستم اعلان‌ها")
    print("=" * 50)
    
    # دریافت کاربر admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # پاکسازی اعلان‌های قدیمی
    old_notifications = Notification.objects.filter(
        recipient=admin_user,
        description__icontains='تست'
    )
    deleted_count = old_notifications.count()
    old_notifications.delete()
    if deleted_count > 0:
        print(f"🗑️ {deleted_count} اعلان قدیمی حذف شد")
    
    # ایجاد اعلان‌های مختلف
    test_cases = [
        {
            'name': 'اعلان مهم سیستم',
            'verb': 'سیستم را راه‌اندازی کرد',
            'description': 'سیستم با موفقیت راه‌اندازی شد',
            'entity_type': 'system',
            'priority': 'high'
        },
        {
            'name': 'اعلان بودجه',
            'verb': 'بودجه جدید ایجاد کرد',
            'description': 'بودجه پروژه جدید تایید شد',
            'entity_type': 'budget',
            'priority': 'high'
        },
        {
            'name': 'اعلان تنخواه',
            'verb': 'تنخواه جدید ثبت کرد',
            'description': 'درخواست تنخواه جدید دریافت شد',
            'entity_type': 'tankhah',
            'priority': 'medium'
        },
        {
            'name': 'اعلان فاکتور',
            'verb': 'فاکتور جدید صادر کرد',
            'description': 'فاکتور شماره 12345 صادر شد',
            'entity_type': 'factor',
            'priority': 'medium'
        },
        {
            'name': 'اعلان پرداخت',
            'verb': 'پرداخت جدید انجام داد',
            'description': 'پرداخت سفارش تایید شد',
            'entity_type': 'payment',
            'priority': 'high'
        }
    ]
    
    print(f"\n📢 ایجاد {len(test_cases)} اعلان تستی...")
    
    created_notifications = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        notification = Notification.objects.create(
            recipient=admin_user,
            actor=admin_user,
            verb=test_case['verb'],
            description=test_case['description'],
            entity_type=test_case['entity_type'],
            priority=test_case['priority'],
            timestamp=timezone.now() + timedelta(seconds=i)
        )
        
        created_notifications.append(notification)
        print(f"   ✅ ایجاد شد: {test_case['description']}")
        
        # نمایش آمار
        unread_count = Notification.objects.filter(
            recipient=admin_user, 
            unread=True
        ).count()
        print(f"   🔔 اعلان‌های خوانده‌نشده: {unread_count}")
        
        # تاخیر برای مشاهده انیمیشن‌ها
        if i < len(test_cases):
            time.sleep(2)
    
    # نمایش آمار نهایی
    print(f"\n📊 آمار نهایی:")
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
    print(f"   - اعلان‌های تستی ایجاد شده: {len(created_notifications)}")
    
    # نمایش انواع اعلان‌ها
    print(f"\n📋 انواع اعلان‌های ایجاد شده:")
    entity_types = {}
    for notif in created_notifications:
        entity_type = notif.entity_type
        if entity_type not in entity_types:
            entity_types[entity_type] = 0
        entity_types[entity_type] += 1
    
    for entity_type, count in entity_types.items():
        print(f"   - {entity_type}: {count} اعلان")
    
    # دستورالعمل تست
    print(f"\n🎯 دستورالعمل تست:")
    print(f"   1. به پنل ادمین بروید: http://127.0.0.1:8000/admin/")
    print(f"   2. زنگوله باید {unread_notifications} اعلان نشان دهد")
    print(f"   3. انیمیشن‌های زیر باید فعال باشند:")
    print(f"      - انیمیشن shake (لرزش)")
    print(f"      - انیمیشن pulse (ضربان)")
    print(f"      - انیمیشن bounce (جهش badge)")
    print(f"   4. روی زنگوله کلیک کنید تا اعلان‌ها را ببینید")
    print(f"   5. اعلان‌های خوانده‌نشده باید با رنگ آبی نمایش داده شوند")
    
    # تست عملکرد JavaScript
    print(f"\n🔧 تست عملکرد JavaScript:")
    print(f"   - تابع fetchNotifications() باید کار کند")
    print(f"   - تابع updateNotificationBadge() باید انیمیشن‌ها را فعال کند")
    print(f"   - AJAX requests باید موفق باشند")
    print(f"   - Console errors نباید وجود داشته باشد")
    
    return created_notifications

def test_notification_rules():
    """تست قوانین اعلان‌ها"""
    
    print(f"\n📜 تست قوانین اعلان‌ها:")
    
    rules = NotificationRule.objects.all()
    if rules.exists():
        print(f"   ✅ {rules.count()} قانون اعلان یافت شد")
        for rule in rules:
            print(f"      - {rule.get_action_display()}: {rule.get_entity_type_display()}")
    else:
        print(f"   ⚠️ هیچ قانون اعلانی یافت نشد")
        print(f"   💡 برای ایجاد قوانین از اسکریپت setup_notification_signals.py استفاده کنید")

def cleanup_test_data():
    """پاکسازی داده‌های تست"""
    
    print(f"\n🧹 پاکسازی داده‌های تست...")
    
    try:
        admin_user = User.objects.get(username='admin')
        test_notifications = Notification.objects.filter(
            recipient=admin_user,
            description__icontains='تست'
        )
        deleted_count = test_notifications.count()
        test_notifications.delete()
        print(f"✅ {deleted_count} اعلان تستی حذف شد")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تست کامل سیستم اعلان‌ها')
    parser.add_argument('--cleanup', action='store_true', help='پاکسازی داده‌های تست')
    parser.add_argument('--rules', action='store_true', help='تست قوانین اعلان‌ها')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_data()
    elif args.rules:
        test_notification_rules()
    else:
        test_complete_notification_system()
        test_notification_rules()
