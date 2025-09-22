#!/usr/bin/env python
"""
اسکریپت تست اعلان برای admin
این اسکریپت اعلان‌های تستی مختلف برای admin ایجاد می‌کند
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

def create_test_notifications():
    """ایجاد اعلان‌های تستی برای admin"""
    print("🔔 ایجاد اعلان‌های تستی برای admin...")
    print("=" * 60)
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
        
        # ایجاد اعلان‌های تستی مختلف
        test_notifications = [
            {
                'verb': 'CREATED',
                'description': 'سیستم USB Dongle با موفقیت راه‌اندازی شد',
                'entity_type': 'SYSTEM',
                'priority': 'HIGH'
            },
            {
                'verb': 'STARTED',
                'description': 'پشتیبان‌گیری خودکار دیتابیس شروع شد',
                'entity_type': 'BACKUP',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'COMPLETED',
                'description': 'پشتیبان‌گیری دیتابیس با موفقیت تکمیل شد',
                'entity_type': 'BACKUP',
                'priority': 'LOW'
            },
            {
                'verb': 'WARNING',
                'description': 'حجم دیتابیس به 80% ظرفیت رسیده است',
                'entity_type': 'MAINTENANCE',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': 'خطا در اتصال به سرویس پشتیبان‌گیری',
                'entity_type': 'SYSTEM',
                'priority': 'ERROR'
            },
            {
                'verb': 'LOCKED',
                'description': 'قفل سیستم فعال شد - دسترسی محدود',
                'entity_type': 'SECURITY',
                'priority': 'LOCKED'
            }
        ]
        
        created_notifications = []
        
        for i, notif_data in enumerate(test_notifications, 1):
            print(f"\n📝 ایجاد اعلان {i}: {notif_data['description']}")
            
            # ایجاد اعلان
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,  # سیستم
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=i*5)  # اعلان‌های مختلف در زمان‌های مختلف
            )
            
            created_notifications.append(notification)
            print(f"   ✅ اعلان ایجاد شد (ID: {notification.id})")
        
        print(f"\n🎉 {len(created_notifications)} اعلان تستی ایجاد شد!")
        
        # نمایش آمار
        total_notifications = admin_user.notifications.filter(deleted=False).count()
        unread_notifications = admin_user.notifications.filter(unread=True, deleted=False).count()
        
        print(f"\n📊 آمار اعلان‌ها:")
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های تستی: {e}")
        return False

def create_notification_rules():
    """ایجاد قوانین اعلان برای admin"""
    print("\n🔧 ایجاد قوانین اعلان...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # ایجاد قوانین اعلان
        rules_data = [
            {
                'entity_type': 'SYSTEM',
                'action': 'CREATED',
                'priority': 'HIGH',
                'channel': 'IN_APP'
            },
            {
                'entity_type': 'BACKUP',
                'action': 'STARTED',
                'priority': 'MEDIUM',
                'channel': 'IN_APP'
            },
            {
                'entity_type': 'BACKUP',
                'action': 'COMPLETED',
                'priority': 'LOW',
                'channel': 'IN_APP'
            },
            {
                'entity_type': 'MAINTENANCE',
                'action': 'WARNING',
                'priority': 'WARNING',
                'channel': 'IN_APP'
            },
            {
                'entity_type': 'SYSTEM',
                'action': 'ERROR',
                'priority': 'ERROR',
                'channel': 'IN_APP'
            },
            {
                'entity_type': 'SECURITY',
                'action': 'LOCKED',
                'priority': 'LOCKED',
                'channel': 'IN_APP'
            }
        ]
        
        created_rules = []
        
        for rule_data in rules_data:
            # بررسی وجود قانون
            existing_rule = NotificationRule.objects.filter(
                entity_type=rule_data['entity_type'],
                action=rule_data['action']
            ).first()
            
            if existing_rule:
                print(f"   ⚠️  قانون {rule_data['entity_type']} - {rule_data['action']} قبلاً وجود دارد")
                continue
            
            # ایجاد قانون جدید
            rule = NotificationRule.objects.create(
                entity_type=rule_data['entity_type'],
                action=rule_data['action'],
                priority=rule_data['priority'],
                channel=rule_data['channel'],
                is_active=True
            )
            
            created_rules.append(rule)
            print(f"   ✅ قانون ایجاد شد: {rule}")
        
        print(f"\n🎉 {len(created_rules)} قانون اعلان ایجاد شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد قوانین اعلان: {e}")
        return False

def test_notification_sending():
    """تست ارسال اعلان"""
    print("\n📤 تست ارسال اعلان...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # ارسال اعلان تستی
        send_notification(
            sender=None,  # سیستم
            users=[admin_user],
            verb='TEST',
            description='این یک اعلان تستی است - سیستم اعلان‌ها به درستی کار می‌کند',
            entity_type='SYSTEM',
            priority='MEDIUM'
        )
        
        print("✅ اعلان تستی ارسال شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ارسال اعلان تستی: {e}")
        return False

def show_notification_stats():
    """نمایش آمار اعلان‌ها"""
    print("\n📊 آمار اعلان‌ها:")
    print("=" * 60)
    
    try:
        # آمار کلی
        total_notifications = Notification.objects.filter(deleted=False).count()
        unread_notifications = Notification.objects.filter(unread=True, deleted=False).count()
        
        print(f"📈 آمار کلی:")
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
        print(f"   - اعلان‌های خوانده‌شده: {total_notifications - unread_notifications}")
        
        # آمار بر اساس اولویت
        print(f"\n🎯 آمار بر اساس اولویت:")
        priorities = ['LOW', 'MEDIUM', 'HIGH', 'WARNING', 'ERROR', 'LOCKED']
        for priority in priorities:
            count = Notification.objects.filter(priority=priority, deleted=False).count()
            print(f"   - {priority}: {count}")
        
        # آمار بر اساس نوع موجودیت
        print(f"\n📋 آمار بر اساس نوع موجودیت:")
        entity_types = ['FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BACKUP', 'SYSTEM', 'SECURITY', 'MAINTENANCE']
        for entity_type in entity_types:
            count = Notification.objects.filter(entity_type=entity_type, deleted=False).count()
            print(f"   - {entity_type}: {count}")
        
        # آمار بر اساس کاربر
        print(f"\n👤 آمار بر اساس کاربر:")
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        for admin_user in admin_users:
            user_notifications = admin_user.notifications.filter(deleted=False).count()
            user_unread = admin_user.notifications.filter(unread=True, deleted=False).count()
            print(f"   - {admin_user.username}: {user_notifications} (خوانده‌نشده: {user_unread})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔔 تست سیستم اعلان‌ها برای Admin")
    print("=" * 60)
    
    try:
        # ایجاد قوانین اعلان
        create_notification_rules()
        
        # ایجاد اعلان‌های تستی
        create_test_notifications()
        
        # تست ارسال اعلان
        test_notification_sending()
        
        # نمایش آمار
        show_notification_stats()
        
        print(f"\n🎉 تست سیستم اعلان‌ها با موفقیت انجام شد!")
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
