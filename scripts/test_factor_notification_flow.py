#!/usr/bin/env python
"""
تست روند اعلان‌ها هنگام ثبت فاکتور
این اسکریپت روند کامل اعلان‌ها را هنگام ثبت فاکتور شبیه‌سازی می‌کند
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
from notificationApp.utils import send_notification
from core.models import Post
from django.utils import timezone

User = get_user_model()

def test_factor_notification_flow():
    """تست روند اعلان‌ها هنگام ثبت فاکتور"""
    
    print("🔔 تست روند اعلان‌ها هنگام ثبت فاکتور")
    print("=" * 60)
    
    # دریافت کاربر admin به عنوان ایجادکننده فاکتور
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ کاربر ایجادکننده: {admin_user.username} ({admin_user.first_name} {admin_user.last_name})")
    except User.DoesNotExist:
        print("❌ کاربر admin یافت نشد!")
        return
    
    # بررسی قوانین اعلان برای فاکتور
    print(f"\n📋 بررسی قوانین اعلان برای فاکتور:")
    factor_rules = NotificationRule.objects.filter(entity_type='FACTOR', is_active=True)
    print(f"   - تعداد قوانین فعال: {factor_rules.count()}")
    
    # شبیه‌سازی ایجاد فاکتور
    print(f"\n📄 شبیه‌سازی ایجاد فاکتور:")
    print(f"   - ایجادکننده: {admin_user.username}")
    print(f"   - شماره فاکتور: FA-2024-001")
    print(f"   - عنوان: فاکتور تست سیستم اعلان‌ها")
    
    # ارسال اعلان ایجاد فاکتور
    print(f"\n🔔 ارسال اعلان ایجاد فاکتور:")
    
    # پیدا کردن پست‌های مربوط به قوانین اعلان
    creation_rules = NotificationRule.objects.filter(
        entity_type='FACTOR',
        action='CREATED',
        is_active=True
    )
    
    if creation_rules.exists():
        for rule in creation_rules:
            print(f"   📋 قانون: {rule.get_action_display()} - {rule.get_entity_type_display()}")
            print(f"      - اولویت: {rule.get_priority_display()}")
            print(f"      - کانال: {rule.get_channel_display()}")
            
            # ارسال اعلان به گیرندگان
            recipients = rule.recipients.all()
            if recipients.exists():
                print(f"      - گیرندگان:")
                for post in recipients:
                    from notificationApp.utils import get_users_for_post
                    users = get_users_for_post(post)
                    print(f"        * پست: {post.name}")
                    if users:
                        for user in users:
                            print(f"          - {user.username} ({user.first_name} {user.last_name})")
                            
                            # ایجاد اعلان
                            notification = Notification.objects.create(
                                recipient=user,
                                actor=admin_user,
                                verb='CREATED',
                                description=f'فاکتور جدید "FA-2024-001" ایجاد شد',
                                entity_type='FACTOR',
                                priority=rule.priority,
                                timestamp=timezone.now()
                            )
                            print(f"            ✅ اعلان ایجاد شد: ID {notification.id}")
                    else:
                        print(f"          - هیچ کاربر فعالی در این پست نیست")
            else:
                print(f"      - هیچ گیرنده‌ای تعریف نشده")
    else:
        print(f"   ⚠️ هیچ قانون اعلانی برای ایجاد فاکتور یافت نشد")
    
    # شبیه‌سازی تأیید فاکتور
    print(f"\n✅ شبیه‌سازی تأیید فاکتور:")
    
    approval_rules = NotificationRule.objects.filter(
        entity_type='FACTOR',
        action='APPROVED',
        is_active=True
    )
    
    if approval_rules.exists():
        for rule in approval_rules:
            print(f"   📋 قانون: {rule.get_action_display()} - {rule.get_entity_type_display()}")
            
            recipients = rule.recipients.all()
            if recipients.exists():
                for post in recipients:
                    from notificationApp.utils import get_users_for_post
                    users = get_users_for_post(post)
                    if users:
                        for user in users:
                            notification = Notification.objects.create(
                                recipient=user,
                                actor=admin_user,
                                verb='APPROVED',
                                description=f'فاکتور "FA-2024-001" تأیید شد',
                                entity_type='FACTOR',
                                priority=rule.priority,
                                timestamp=timezone.now()
                            )
                            print(f"     ✅ اعلان تأیید ایجاد شد برای {user.username}: ID {notification.id}")
    else:
        print(f"   ⚠️ هیچ قانون اعلانی برای تأیید فاکتور یافت نشد")
    
    # نمایش آمار نهایی
    print(f"\n📊 آمار نهایی اعلان‌ها:")
    total_notifications = Notification.objects.filter(recipient=admin_user).count()
    unread_notifications = Notification.objects.filter(
        recipient=admin_user, 
        unread=True
    ).count()
    
    print(f"   - کل اعلان‌ها: {total_notifications}")
    print(f"   - اعلان‌های خوانده‌نشده: {unread_notifications}")
    
    # نمایش اعلان‌های جدید ایجاد شده
    recent_notifications = Notification.objects.filter(
        description__icontains='FA-2024-001'
    ).order_by('-timestamp')
    
    print(f"\n🔔 اعلان‌های جدید ایجاد شده:")
    for notif in recent_notifications:
        print(f"   - {notif.recipient.username}: {notif.description} ({notif.get_priority_display()})")
    
    print(f"\n🎯 برای مشاهده اعلان‌ها:")
    print(f"   1. به پنل ادمین بروید: http://127.0.0.1:8000/admin/")
    print(f"   2. زنگوله باید {unread_notifications} اعلان نشان دهد")
    print(f"   3. انیمیشن‌های shake و pulse باید فعال باشند")

def show_notification_flow_summary():
    """نمایش خلاصه روند اعلان‌ها"""
    
    print(f"\n📋 خلاصه روند اعلان‌ها هنگام ثبت فاکتور:")
    print(f"=" * 60)
    
    print(f"1️⃣ هنگام ایجاد فاکتور:")
    print(f"   - اعلان به کاربران پست 'کارشناس مالی تنخواه گردان شعبات' ارسال می‌شود")
    print(f"   - گیرنده: snejate (سجاد نجاتی)")
    
    print(f"\n2️⃣ هنگام تأیید فاکتور:")
    print(f"   - اعلان به مدیران شعبات ارسال می‌شود")
    print(f"   - گیرندگان: beygh, manager_هتل_لاله_تهران, و سایر مدیران")
    
    print(f"\n3️⃣ هنگام پرداخت فاکتور:")
    print(f"   - اعلان به معاونت مالی و مدیرعامل ارسال می‌شود")
    print(f"   - گیرندگان: rheyran, admin, kgo, بانک")
    
    print(f"\n4️⃣ ویژگی‌های اعلان‌ها:")
    print(f"   - انیمیشن لرزش (shake) هنگام اعلان جدید")
    print(f"   - انیمیشن ضربان (pulse) برای زنگوله")
    print(f"   - اولویت‌های مختلف (کم، متوسط، زیاد)")
    print(f"   - به‌روزرسانی real-time هر 30 ثانیه")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تست روند اعلان‌ها هنگام ثبت فاکتور')
    parser.add_argument('--summary', action='store_true', help='نمایش خلاصه روند اعلان‌ها')
    
    args = parser.parse_args()
    
    if args.summary:
        show_notification_flow_summary()
    else:
        test_factor_notification_flow()
        show_notification_flow_summary()
