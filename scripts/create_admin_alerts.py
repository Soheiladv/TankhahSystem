#!/usr/bin/env python
"""
اسکریپت ایجاد اعلان‌های مختلف برای admin
این اسکریپت اعلان‌های مختلف سیستم، امنیت، پشتیبان‌گیری و نگهداری برای admin ایجاد می‌کند
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

def create_system_notifications():
    """ایجاد اعلان‌های سیستم"""
    print("🖥️ ایجاد اعلان‌های سیستم...")
    
    try:
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        system_notifications = [
            {
                'verb': 'CREATED',
                'description': 'سیستم USB Dongle با موفقیت راه‌اندازی شد',
                'entity_type': 'SYSTEM',
                'priority': 'HIGH'
            },
            {
                'verb': 'STARTED',
                'description': 'سرور Django با دسترسی ادمین شروع شد',
                'entity_type': 'SYSTEM',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'COMPLETED',
                'description': 'به‌روزرسانی سیستم با موفقیت تکمیل شد',
                'entity_type': 'SYSTEM',
                'priority': 'LOW'
            },
            {
                'verb': 'ERROR',
                'description': 'خطا در اتصال به سرویس پشتیبان‌گیری',
                'entity_type': 'SYSTEM',
                'priority': 'ERROR'
            },
            {
                'verb': 'WARNING',
                'description': 'حافظه سرور به 85% ظرفیت رسیده است',
                'entity_type': 'SYSTEM',
                'priority': 'WARNING'
            }
        ]
        
        for notif_data in system_notifications:
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 60))
            )
            print(f"   ✅ {notif_data['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های سیستم: {e}")
        return False

def create_security_notifications():
    """ایجاد اعلان‌های امنیت"""
    print("\n🔒 ایجاد اعلان‌های امنیت...")
    
    try:
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            return False
        
        admin_user = admin_users.first()
        
        security_notifications = [
            {
                'verb': 'LOCKED',
                'description': 'قفل سیستم فعال شد - دسترسی محدود',
                'entity_type': 'SECURITY',
                'priority': 'LOCKED'
            },
            {
                'verb': 'WARNING',
                'description': 'تلاش ورود ناموفق از IP نامشخص',
                'entity_type': 'SECURITY',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': 'شناسایی فعالیت مشکوک در سیستم',
                'entity_type': 'SECURITY',
                'priority': 'ERROR'
            },
            {
                'verb': 'CREATED',
                'description': 'کلید امنیتی جدید برای USB Dongle ایجاد شد',
                'entity_type': 'SECURITY',
                'priority': 'HIGH'
            }
        ]
        
        for notif_data in security_notifications:
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 60))
            )
            print(f"   ✅ {notif_data['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های امنیت: {e}")
        return False

def create_backup_notifications():
    """ایجاد اعلان‌های پشتیبان‌گیری"""
    print("\n💾 ایجاد اعلان‌های پشتیبان‌گیری...")
    
    try:
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            return False
        
        admin_user = admin_users.first()
        
        backup_notifications = [
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
                'verb': 'FAILED',
                'description': 'پشتیبان‌گیری دیتابیس ناموفق بود - بررسی نیاز است',
                'entity_type': 'BACKUP',
                'priority': 'ERROR'
            },
            {
                'verb': 'SCHEDULED',
                'description': 'پشتیبان‌گیری زمان‌بندی شده برای فردا تنظیم شد',
                'entity_type': 'BACKUP',
                'priority': 'LOW'
            }
        ]
        
        for notif_data in backup_notifications:
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 60))
            )
            print(f"   ✅ {notif_data['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های پشتیبان‌گیری: {e}")
        return False

def create_maintenance_notifications():
    """ایجاد اعلان‌های نگهداری"""
    print("\n🔧 ایجاد اعلان‌های نگهداری...")
    
    try:
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            return False
        
        admin_user = admin_users.first()
        
        maintenance_notifications = [
            {
                'verb': 'WARNING',
                'description': 'حجم دیتابیس به 80% ظرفیت رسیده است',
                'entity_type': 'MAINTENANCE',
                'priority': 'WARNING'
            },
            {
                'verb': 'SCHEDULED',
                'description': 'تعمیرات برنامه‌ریزی شده برای شنبه آینده',
                'entity_type': 'MAINTENANCE',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'STARTED',
                'description': 'بهینه‌سازی دیتابیس شروع شد',
                'entity_type': 'MAINTENANCE',
                'priority': 'LOW'
            },
            {
                'verb': 'COMPLETED',
                'description': 'پاکسازی فایل‌های موقت تکمیل شد',
                'entity_type': 'MAINTENANCE',
                'priority': 'LOW'
            }
        ]
        
        for notif_data in maintenance_notifications:
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 60))
            )
            print(f"   ✅ {notif_data['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های نگهداری: {e}")
        return False

def create_usb_dongle_notifications():
    """ایجاد اعلان‌های USB Dongle"""
    print("\n🔐 ایجاد اعلان‌های USB Dongle...")
    
    try:
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            return False
        
        admin_user = admin_users.first()
        
        dongle_notifications = [
            {
                'verb': 'CREATED',
                'description': 'USB Dongle جدید برای شرکت "توسعه گردشگری ایران" ایجاد شد',
                'entity_type': 'SECURITY',
                'priority': 'HIGH'
            },
            {
                'verb': 'VALIDATED',
                'description': 'اعتبارسنجی USB Dongle موفق بود',
                'entity_type': 'SECURITY',
                'priority': 'LOW'
            },
            {
                'verb': 'WARNING',
                'description': 'USB Dongle در درایو E: یافت نشد',
                'entity_type': 'SECURITY',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': 'خطا در خواندن سکتورهای USB Dongle',
                'entity_type': 'SECURITY',
                'priority': 'ERROR'
            },
            {
                'verb': 'REPAIRED',
                'description': 'USB Dongle با موفقیت تعمیر شد',
                'entity_type': 'SECURITY',
                'priority': 'MEDIUM'
            }
        ]
        
        for notif_data in dongle_notifications:
            notification = Notification.objects.create(
                recipient=admin_user,
                actor=None,
                verb=notif_data['verb'],
                description=notif_data['description'],
                entity_type=notif_data['entity_type'],
                priority=notif_data['priority'],
                unread=True,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 60))
            )
            print(f"   ✅ {notif_data['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های USB Dongle: {e}")
        return False

def show_final_stats():
    """نمایش آمار نهایی"""
    print("\n📊 آمار نهایی اعلان‌ها:")
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
            if count > 0:
                print(f"   - {priority}: {count}")
        
        # آمار بر اساس نوع موجودیت
        print(f"\n📋 آمار بر اساس نوع موجودیت:")
        entity_types = ['FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BACKUP', 'SYSTEM', 'SECURITY', 'MAINTENANCE']
        for entity_type in entity_types:
            count = Notification.objects.filter(entity_type=entity_type, deleted=False).count()
            if count > 0:
                print(f"   - {entity_type}: {count}")
        
        # آمار بر اساس کاربر
        print(f"\n👤 آمار بر اساس کاربر:")
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        for admin_user in admin_users:
            user_notifications = admin_user.notifications.filter(deleted=False).count()
            user_unread = admin_user.notifications.filter(unread=True, deleted=False).count()
            if user_notifications > 0:
                print(f"   - {admin_user.username}: {user_notifications} (خوانده‌نشده: {user_unread})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔔 ایجاد اعلان‌های مختلف برای Admin")
    print("=" * 60)
    
    try:
        # ایجاد اعلان‌های مختلف
        create_system_notifications()
        create_security_notifications()
        create_backup_notifications()
        create_maintenance_notifications()
        create_usb_dongle_notifications()
        
        # نمایش آمار نهایی
        show_final_stats()
        
        print(f"\n🎉 همه اعلان‌ها با موفقیت ایجاد شدند!")
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        print(f"   http://127.0.0.1:8000/admin/notificationApp/notification/")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
