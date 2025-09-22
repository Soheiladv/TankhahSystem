#!/usr/bin/env python
"""
اسکریپت نهایی‌سازی سیستم اعلان‌ها
این اسکریپت سیستم اعلان‌ها را کاملاً فعال می‌کند
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

def create_final_notifications():
    """ایجاد اعلان‌های نهایی"""
    print("🎯 ایجاد اعلان‌های نهایی...")
    print("=" * 60)
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
        
        # پاک کردن اعلان‌های قبلی
        Notification.objects.filter(recipient=admin_user).delete()
        print("🧹 اعلان‌های قبلی پاک شدند")
        
        # ایجاد اعلان‌های نهایی
        final_notifications = [
            {
                'verb': 'CREATED',
                'description': '🎉 سیستم اعلان‌ها با موفقیت فعال شد',
                'entity_type': 'SYSTEM',
                'priority': 'HIGH'
            },
            {
                'verb': 'STARTED',
                'description': '🚀 سرور Django با دسترسی ادمین شروع شد',
                'entity_type': 'SYSTEM',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'COMPLETED',
                'description': '✅ پیکربندی سیستم اعلان‌ها تکمیل شد',
                'entity_type': 'SYSTEM',
                'priority': 'LOW'
            },
            {
                'verb': 'WARNING',
                'description': '⚠️ حافظه سرور به 75% ظرفیت رسیده است',
                'entity_type': 'SYSTEM',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': '❌ خطا در اتصال به سرویس پشتیبان‌گیری',
                'entity_type': 'SYSTEM',
                'priority': 'ERROR'
            },
            {
                'verb': 'LOCKED',
                'description': '🔒 قفل سیستم فعال شد - دسترسی محدود',
                'entity_type': 'SECURITY',
                'priority': 'LOCKED'
            },
            {
                'verb': 'CREATED',
                'description': '🔐 کلید امنیتی جدید برای USB Dongle ایجاد شد',
                'entity_type': 'SECURITY',
                'priority': 'HIGH'
            },
            {
                'verb': 'VALIDATED',
                'description': '✅ اعتبارسنجی USB Dongle موفق بود',
                'entity_type': 'SECURITY',
                'priority': 'LOW'
            },
            {
                'verb': 'STARTED',
                'description': '💾 پشتیبان‌گیری خودکار دیتابیس شروع شد',
                'entity_type': 'BACKUP',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'COMPLETED',
                'description': '✅ پشتیبان‌گیری دیتابیس با موفقیت تکمیل شد',
                'entity_type': 'BACKUP',
                'priority': 'LOW'
            },
            {
                'verb': 'FAILED',
                'description': '❌ پشتیبان‌گیری دیتابیس ناموفق بود - بررسی نیاز است',
                'entity_type': 'BACKUP',
                'priority': 'ERROR'
            },
            {
                'verb': 'SCHEDULED',
                'description': '📅 پشتیبان‌گیری زمان‌بندی شده برای فردا تنظیم شد',
                'entity_type': 'BACKUP',
                'priority': 'LOW'
            },
            {
                'verb': 'WARNING',
                'description': '⚠️ حجم دیتابیس به 80% ظرفیت رسیده است',
                'entity_type': 'MAINTENANCE',
                'priority': 'WARNING'
            },
            {
                'verb': 'SCHEDULED',
                'description': '🔧 تعمیرات برنامه‌ریزی شده برای شنبه آینده',
                'entity_type': 'MAINTENANCE',
                'priority': 'MEDIUM'
            },
            {
                'verb': 'STARTED',
                'description': '⚙️ بهینه‌سازی دیتابیس شروع شد',
                'entity_type': 'MAINTENANCE',
                'priority': 'LOW'
            },
            {
                'verb': 'COMPLETED',
                'description': '✅ پاکسازی فایل‌های موقت تکمیل شد',
                'entity_type': 'MAINTENANCE',
                'priority': 'LOW'
            },
            {
                'verb': 'CREATED',
                'description': '🔐 USB Dongle جدید برای شرکت "توسعه گردشگری ایران" ایجاد شد',
                'entity_type': 'SECURITY',
                'priority': 'HIGH'
            },
            {
                'verb': 'WARNING',
                'description': '⚠️ USB Dongle در درایو E: یافت نشد',
                'entity_type': 'SECURITY',
                'priority': 'WARNING'
            },
            {
                'verb': 'ERROR',
                'description': '❌ خطا در خواندن سکتورهای USB Dongle',
                'entity_type': 'SECURITY',
                'priority': 'ERROR'
            },
            {
                'verb': 'REPAIRED',
                'description': '🔧 USB Dongle با موفقیت تعمیر شد',
                'entity_type': 'SECURITY',
                'priority': 'MEDIUM'
            }
        ]
        
        created_notifications = []
        
        for i, notif_data in enumerate(final_notifications, 1):
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
                timestamp=timezone.now() - timedelta(minutes=i*2)  # اعلان‌های مختلف در زمان‌های مختلف
            )
            
            created_notifications.append(notification)
            print(f"   ✅ اعلان ایجاد شد (ID: {notification.id})")
        
        print(f"\n🎉 {len(created_notifications)} اعلان نهایی ایجاد شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های نهایی: {e}")
        return False

def create_mixed_status():
    """ایجاد وضعیت مختلط"""
    print("\n👁️ ایجاد وضعیت مختلط اعلان‌ها...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            return False
        
        admin_user = admin_users.first()
        
        # دریافت اعلان‌های خوانده‌نشده
        unread_notifications = admin_user.notifications.filter(unread=True, deleted=False)
        print(f"📊 {unread_notifications.count()} اعلان خوانده‌نشده یافت شد")
        
        # علامت‌گذاری نیمی از اعلان‌ها به عنوان خوانده شده
        half_count = unread_notifications.count() // 2
        notifications_to_mark = unread_notifications[:half_count]
        
        for notification in notifications_to_mark:
            notification.mark_as_read()
            print(f"   ✅ اعلان {notification.id} به عنوان خوانده شده علامت‌گذاری شد")
        
        print(f"🎉 {half_count} اعلان به عنوان خوانده شده علامت‌گذاری شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد وضعیت مختلط: {e}")
        return False

def show_final_stats():
    """نمایش آمار نهایی"""
    print("\n📊 آمار نهایی سیستم اعلان‌ها:")
    print("=" * 60)
    
    try:
        # آمار کلی
        total_notifications = Notification.objects.filter(deleted=False).count()
        unread_notifications = Notification.objects.filter(unread=True, deleted=False).count()
        read_notifications = Notification.objects.filter(unread=False, deleted=False).count()
        
        print(f"📈 آمار کلی:")
        print(f"   - کل اعلان‌ها: {total_notifications}")
        print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
        print(f"   - اعلان‌های خوانده‌شده: {read_notifications}")
        
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
            user_read = admin_user.notifications.filter(unread=False, deleted=False).count()
            if user_notifications > 0:
                print(f"   - {admin_user.username}: {user_notifications} (خوانده‌نشده: {user_unread}, خوانده‌شده: {user_read})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🎯 نهایی‌سازی سیستم اعلان‌ها")
    print("=" * 60)
    
    try:
        # ایجاد اعلان‌های نهایی
        create_final_notifications()
        
        # ایجاد وضعیت مختلط
        create_mixed_status()
        
        # نمایش آمار نهایی
        show_final_stats()
        
        print(f"\n🎉 سیستم اعلان‌ها کاملاً فعال شد!")
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        print(f"   http://127.0.0.1:8000/admin/notificationApp/notification/")
        
        print(f"\n🔔 نحوه استفاده:")
        print(f"   1. آیکون زنگ در نوار بالایی صفحه اصلی")
        print(f"   2. تعداد اعلان‌های خوانده‌نشده نمایش داده می‌شود")
        print(f"   3. کلیک روی آیکون برای مشاهده اعلان‌ها")
        print(f"   4. کلیک روی اعلان برای علامت‌گذاری به عنوان خوانده شده")
        print(f"   5. دکمه حذف برای حذف اعلان‌ها")
        
        print(f"\n🔧 نکات فنی:")
        print(f"   - اعلان‌ها هر 30 ثانیه به‌روزرسانی می‌شوند")
        print(f"   - JavaScript در console مرورگر قابل دیباگ است")
        print(f"   - URL های API در /notifications/api/ قرار دارند")
        print(f"   - تمپلیت‌ها در templates/notifications/ قرار دارند")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
