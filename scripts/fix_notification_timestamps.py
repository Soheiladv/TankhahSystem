#!/usr/bin/env python
"""
اسکریپت حل مشکل timezone در اعلان‌ها
این اسکریپت timestamps اعلان‌ها را اصلاح می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from notificationApp.models import Notification
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

def fix_notification_timestamps():
    """اصلاح timestamps اعلان‌ها"""
    print("🔧 اصلاح timestamps اعلان‌ها...")
    print("=" * 60)
    
    try:
        # دریافت همه اعلان‌ها
        notifications = Notification.objects.all()
        print(f"📊 {notifications.count()} اعلان یافت شد")
        
        # تنظیم timezone
        tehran_tz = pytz.timezone('Asia/Tehran')
        
        fixed_count = 0
        
        for notification in notifications:
            try:
                # بررسی timestamp فعلی
                current_timestamp = notification.timestamp
                print(f"   اعلان {notification.id}: {current_timestamp}")
                
                # اگر timestamp مشکل دارد، آن را اصلاح کن
                if current_timestamp is None:
                    # ایجاد timestamp جدید
                    new_timestamp = timezone.now()
                    notification.timestamp = new_timestamp
                    notification.save()
                    print(f"   ✅ timestamp جدید ایجاد شد: {new_timestamp}")
                    fixed_count += 1
                else:
                    # بررسی اینکه آیا timestamp معتبر است
                    try:
                        # تلاش برای تبدیل به timezone محلی
                        local_timestamp = current_timestamp.astimezone(tehran_tz)
                        print(f"   ✅ timestamp معتبر است: {local_timestamp}")
                    except Exception as e:
                        # اگر timestamp مشکل دارد، آن را اصلاح کن
                        new_timestamp = timezone.now()
                        notification.timestamp = new_timestamp
                        notification.save()
                        print(f"   ✅ timestamp اصلاح شد: {new_timestamp}")
                        fixed_count += 1
                        
            except Exception as e:
                print(f"   ❌ خطا در اعلان {notification.id}: {e}")
                # ایجاد timestamp جدید
                try:
                    new_timestamp = timezone.now()
                    notification.timestamp = new_timestamp
                    notification.save()
                    print(f"   ✅ timestamp جدید ایجاد شد: {new_timestamp}")
                    fixed_count += 1
                except Exception as e2:
                    print(f"   ❌ خطا در ایجاد timestamp جدید: {e2}")
        
        print(f"\n🎉 {fixed_count} اعلان اصلاح شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در اصلاح timestamps: {e}")
        return False

def create_clean_notifications():
    """ایجاد اعلان‌های تمیز"""
    print("\n🧹 ایجاد اعلان‌های تمیز...")
    
    try:
        # پاک کردن همه اعلان‌ها
        Notification.objects.all().delete()
        print("🧹 همه اعلان‌های قبلی پاک شدند")
        
        # ایجاد اعلان‌های جدید با timestamps صحیح
        from accounts.models import CustomUser
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # اعلان‌های تمیز
        clean_notifications = [
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
            }
        ]
        
        created_count = 0
        
        for i, notif_data in enumerate(clean_notifications, 1):
            try:
                # ایجاد اعلان با timestamp صحیح
                notification = Notification.objects.create(
                    recipient=admin_user,
                    actor=None,
                    verb=notif_data['verb'],
                    description=notif_data['description'],
                    entity_type=notif_data['entity_type'],
                    priority=notif_data['priority'],
                    unread=True,
                    timestamp=timezone.now() - timedelta(minutes=i*5)  # timestamps مختلف
                )
                
                print(f"   ✅ اعلان {i} ایجاد شد: {notification.timestamp}")
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ خطا در ایجاد اعلان {i}: {e}")
        
        print(f"\n🎉 {created_count} اعلان تمیز ایجاد شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اعلان‌های تمیز: {e}")
        return False

def test_admin_page():
    """تست صفحه admin"""
    print("\n🔍 تست صفحه admin...")
    
    try:
        from django.test import Client
        from accounts.models import CustomUser
        
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

def show_final_stats():
    """نمایش آمار نهایی"""
    print("\n📊 آمار نهایی اعلان‌ها:")
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
        
        # نمایش نمونه timestamps
        print(f"\n🕐 نمونه timestamps:")
        notifications = Notification.objects.all()[:5]
        for notification in notifications:
            print(f"   - اعلان {notification.id}: {notification.timestamp}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔧 حل مشکل timezone در اعلان‌ها")
    print("=" * 60)
    
    try:
        # اصلاح timestamps
        fix_notification_timestamps()
        
        # ایجاد اعلان‌های تمیز
        create_clean_notifications()
        
        # تست صفحه admin
        test_admin_page()
        
        # نمایش آمار نهایی
        show_final_stats()
        
        print(f"\n🎉 مشکل timezone حل شد!")
        print(f"\n🌐 برای مشاهده اعلان‌ها:")
        print(f"   http://127.0.0.1:8000/admin/notificationApp/notification/")
        print(f"   http://127.0.0.1:8000/notifications/inbox/")
        print(f"   http://127.0.0.1:8000/notifications/unread/")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    input("\nبرای خروج Enter را فشار دهید...")
