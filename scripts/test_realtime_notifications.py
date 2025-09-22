#!/usr/bin/env python
"""
اسکریپت تست اعلان‌های real-time
این اسکریپت اعلان‌های جدید را با تاخیر ایجاد می‌کند تا انیمیشن‌ها را تست کنیم
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
from notificationApp.models import Notification
from django.utils import timezone

User = get_user_model()

def create_realtime_notifications():
    """ایجاد اعلان‌های real-time برای تست انیمیشن‌ها"""
    
    print("🔔 شروع تست اعلان‌های real-time...")
    
    # دریافت کاربر admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر admin یافت شد: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # اعلان‌های real-time
    realtime_notifications = [
        {
            'verb': 'فایل جدید آپلود کرد',
            'description': 'فایل گزارش ماهانه آپلود شد',
            'entity_type': 'file',
            'priority': 'medium'
        },
        {
            'verb': 'بودجه جدید ایجاد کرد',
            'description': 'بودجه پروژه جدید تایید شد',
            'entity_type': 'budget',
            'priority': 'high'
        },
        {
            'verb': 'تنخواه جدید ثبت کرد',
            'description': 'درخواست تنخواه جدید دریافت شد',
            'entity_type': 'tankhah',
            'priority': 'high'
        },
        {
            'verb': 'فاکتور جدید صادر کرد',
            'description': 'فاکتور شماره 12345 صادر شد',
            'entity_type': 'factor',
            'priority': 'medium'
        },
        {
            'verb': 'پرداخت جدید انجام داد',
            'description': 'پرداخت سفارش تایید شد',
            'entity_type': 'payment',
            'priority': 'high'
        }
    ]
    
    print(f"\n⏰ ایجاد {len(realtime_notifications)} اعلان با تاخیر 3 ثانیه...")
    print(f"💡 در این زمان زنگوله باید انیمیشن‌های مختلف نشان دهد")
    
    for i, notif_data in enumerate(realtime_notifications, 1):
        print(f"\n📢 ایجاد اعلان {i}/{len(realtime_notifications)}...")
        
        notification = Notification.objects.create(
            recipient=admin_user,
            actor=admin_user,
            verb=notif_data['verb'],
            description=notif_data['description'],
            entity_type=notif_data['entity_type'],
            priority=notif_data['priority'],
            timestamp=timezone.now()
        )
        
        print(f"✅ اعلان ایجاد شد: {notif_data['description']}")
        
        # نمایش آمار فعلی
        unread_count = Notification.objects.filter(
            recipient=admin_user, 
            unread=True
        ).count()
        print(f"🔔 تعداد اعلان‌های خوانده‌نشده: {unread_count}")
        
        if i < len(realtime_notifications):
            print(f"⏳ انتظار 3 ثانیه برای اعلان بعدی...")
            time.sleep(3)
    
    print(f"\n🎉 تست اعلان‌های real-time تکمیل شد!")
    print(f"📊 آمار نهایی:")
    
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
    
    print(f"\n🎯 برای مشاهده انیمیشن‌ها:")
    print(f"   1. به پنل ادمین بروید: http://127.0.0.1:8000/admin/")
    print(f"   2. زنگوله باید {unread_notifications} اعلان نشان دهد")
    print(f"   3. انیمیشن‌های shake و pulse باید فعال باشند")
    print(f"   4. روی زنگوله کلیک کنید تا اعلان‌ها را ببینید")

def test_notification_sounds():
    """تست صداهای اعلان (اختیاری)"""
    
    print(f"\n🔊 تست صداهای اعلان:")
    print(f"   - می‌توانید صداهای اعلان را در JavaScript اضافه کنید")
    print(f"   - استفاده از Web Audio API یا HTML5 Audio")
    print(f"   - صداهای مختلف برای اولویت‌های مختلف")
    
    # مثال کد JavaScript برای صدا
    js_code = """
    // اضافه کردن صدا به اعلان‌ها
    function playNotificationSound(priority) {
        const audio = new Audio();
        switch(priority) {
            case 'high':
                audio.src = '/static/sounds/notification-high.mp3';
                break;
            case 'medium':
                audio.src = '/static/sounds/notification-medium.mp3';
                break;
            case 'low':
                audio.src = '/static/sounds/notification-low.mp3';
                break;
        }
        audio.play().catch(e => console.log('صدا پخش نشد:', e));
    }
    
    // فراخوانی در تابع updateNotificationBadge
    if (count > previousCount) {
        playNotificationSound('high');
    }
    """
    
    print(f"💡 کد JavaScript پیشنهادی:")
    print(js_code)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تست اعلان‌های real-time')
    parser.add_argument('--sounds', action='store_true', help='نمایش اطلاعات صداهای اعلان')
    
    args = parser.parse_args()
    
    if args.sounds:
        test_notification_sounds()
    else:
        create_realtime_notifications()
        test_notification_sounds()
