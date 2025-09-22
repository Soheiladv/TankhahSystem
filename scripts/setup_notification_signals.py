#!/usr/bin/env python
"""
اسکریپت راه‌اندازی سیگنال‌های اعلان برای عملیات‌های مختلف
این اسکریپت اعلان‌ها را برای فاکتور، بودجه، تنخواه و سایر عملیات‌ها فعال می‌کند
"""

import os
import sys
import django

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from notificationApp.utils import send_notification
from accounts.models import CustomUser
from core.models import Post
from tankhah.models import Tankhah, Factor
from budgets.models import BudgetTransaction, PaymentOrder
import logging

logger = logging.getLogger(__name__)

def setup_tankhah_notifications():
    """راه‌اندازی اعلان‌ها برای تنخواه"""
    print("💰 راه‌اندازی اعلان‌ها برای تنخواه...")
    
    @receiver(post_save, sender=Tankhah)
    def tankhah_notification(sender, instance, created, **kwargs):
        try:
            if created:
                # اعلان ایجاد تنخواه
                send_notification(
                    sender=instance.created_by,
                    users=[instance.created_by],
                    verb='CREATED',
                    description=f'تنخواه جدید "{instance.title}" ایجاد شد',
                    target=instance,
                    entity_type='TANKHAH',
                    priority='MEDIUM'
                )
                print(f"   ✅ اعلان ایجاد تنخواه: {instance.title}")
            else:
                # اعلان به‌روزرسانی تنخواه
                send_notification(
                    sender=instance.updated_by if hasattr(instance, 'updated_by') else instance.created_by,
                    users=[instance.created_by],
                    verb='UPDATED',
                    description=f'تنخواه "{instance.title}" به‌روزرسانی شد',
                    target=instance,
                    entity_type='TANKHAH',
                    priority='LOW'
                )
                print(f"   ✅ اعلان به‌روزرسانی تنخواه: {instance.title}")
        except Exception as e:
            logger.error(f"خطا در اعلان تنخواه: {e}")
    
    print("   ✅ سیگنال‌های تنخواه فعال شدند")

def setup_factor_notifications():
    """راه‌اندازی اعلان‌ها برای فاکتور"""
    print("📄 راه‌اندازی اعلان‌ها برای فاکتور...")
    
    @receiver(post_save, sender=Factor)
    def factor_notification(sender, instance, created, **kwargs):
        try:
            if created:
                # اعلان ایجاد فاکتور
                send_notification(
                    sender=instance.created_by,
                    users=[instance.created_by],
                    verb='CREATED',
                    description=f'فاکتور جدید "{instance.title}" ایجاد شد',
                    target=instance,
                    entity_type='FACTOR',
                    priority='MEDIUM'
                )
                print(f"   ✅ اعلان ایجاد فاکتور: {instance.title}")
            else:
                # اعلان به‌روزرسانی فاکتور
                send_notification(
                    sender=instance.updated_by if hasattr(instance, 'updated_by') else instance.created_by,
                    users=[instance.created_by],
                    verb='UPDATED',
                    description=f'فاکتور "{instance.title}" به‌روزرسانی شد',
                    target=instance,
                    entity_type='FACTOR',
                    priority='LOW'
                )
                print(f"   ✅ اعلان به‌روزرسانی فاکتور: {instance.title}")
        except Exception as e:
            logger.error(f"خطا در اعلان فاکتور: {e}")
    
    print("   ✅ سیگنال‌های فاکتور فعال شدند")

def setup_budget_notifications():
    """راه‌اندازی اعلان‌ها برای بودجه"""
    print("💵 راه‌اندازی اعلان‌ها برای بودجه...")
    
    @receiver(post_save, sender=BudgetTransaction)
    def budget_notification(sender, instance, created, **kwargs):
        try:
            if created:
                # اعلان ایجاد تراکنش بودجه
                send_notification(
                    sender=instance.created_by,
                    users=[instance.created_by],
                    verb='CREATED',
                    description=f'تراکنش بودجه جدید "{instance.description}" ایجاد شد',
                    target=instance,
                    entity_type='BUDGET',
                    priority='MEDIUM'
                )
                print(f"   ✅ اعلان ایجاد تراکنش بودجه: {instance.description}")
            else:
                # اعلان به‌روزرسانی تراکنش بودجه
                send_notification(
                    sender=instance.updated_by if hasattr(instance, 'updated_by') else instance.created_by,
                    users=[instance.created_by],
                    verb='UPDATED',
                    description=f'تراکنش بودجه "{instance.description}" به‌روزرسانی شد',
                    target=instance,
                    entity_type='BUDGET',
                    priority='LOW'
                )
                print(f"   ✅ اعلان به‌روزرسانی تراکنش بودجه: {instance.description}")
        except Exception as e:
            logger.error(f"خطا در اعلان بودجه: {e}")
    
    print("   ✅ سیگنال‌های بودجه فعال شدند")

def setup_payment_order_notifications():
    """راه‌اندازی اعلان‌ها برای دستور پرداخت"""
    print("💳 راه‌اندازی اعلان‌ها برای دستور پرداخت...")
    
    @receiver(post_save, sender=PaymentOrder)
    def payment_order_notification(sender, instance, created, **kwargs):
        try:
            if created:
                # اعلان ایجاد دستور پرداخت
                send_notification(
                    sender=instance.created_by,
                    users=[instance.created_by],
                    verb='CREATED',
                    description=f'دستور پرداخت جدید "{instance.title}" ایجاد شد',
                    target=instance,
                    entity_type='PAYMENTORDER',
                    priority='HIGH'
                )
                print(f"   ✅ اعلان ایجاد دستور پرداخت: {instance.title}")
            else:
                # اعلان به‌روزرسانی دستور پرداخت
                send_notification(
                    sender=instance.updated_by if hasattr(instance, 'updated_by') else instance.created_by,
                    users=[instance.created_by],
                    verb='UPDATED',
                    description=f'دستور پرداخت "{instance.title}" به‌روزرسانی شد',
                    target=instance,
                    entity_type='PAYMENTORDER',
                    priority='MEDIUM'
                )
                print(f"   ✅ اعلان به‌روزرسانی دستور پرداخت: {instance.title}")
        except Exception as e:
            logger.error(f"خطا در اعلان دستور پرداخت: {e}")
    
    print("   ✅ سیگنال‌های دستور پرداخت فعال شدند")

def setup_user_notifications():
    """راه‌اندازی اعلان‌ها برای کاربران"""
    print("👤 راه‌اندازی اعلان‌ها برای کاربران...")
    
    @receiver(post_save, sender=CustomUser)
    def user_notification(sender, instance, created, **kwargs):
        try:
            if created:
                # اعلان ایجاد کاربر جدید
                send_notification(
                    sender=None,  # سیستم
                    users=[instance],
                    verb='CREATED',
                    description=f'حساب کاربری جدید "{instance.username}" ایجاد شد',
                    target=instance,
                    entity_type='SYSTEM',
                    priority='LOW'
                )
                print(f"   ✅ اعلان ایجاد کاربر: {instance.username}")
        except Exception as e:
            logger.error(f"خطا در اعلان کاربر: {e}")
    
    print("   ✅ سیگنال‌های کاربر فعال شدند")

def create_notification_rules():
    """ایجاد قوانین اعلان برای عملیات‌های مختلف"""
    print("\n🔧 ایجاد قوانین اعلان...")
    
    try:
        from notificationApp.models import NotificationRule
        
        # قوانین اعلان برای عملیات‌های مختلف
        rules_data = [
            # تنخواه
            {'entity_type': 'TANKHAH', 'action': 'CREATED', 'priority': 'MEDIUM', 'channel': 'IN_APP'},
            {'entity_type': 'TANKHAH', 'action': 'UPDATED', 'priority': 'LOW', 'channel': 'IN_APP'},
            {'entity_type': 'TANKHAH', 'action': 'APPROVED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'TANKHAH', 'action': 'REJECTED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            
            # فاکتور
            {'entity_type': 'FACTOR', 'action': 'CREATED', 'priority': 'MEDIUM', 'channel': 'IN_APP'},
            {'entity_type': 'FACTOR', 'action': 'UPDATED', 'priority': 'LOW', 'channel': 'IN_APP'},
            {'entity_type': 'FACTOR', 'action': 'APPROVED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'FACTOR', 'action': 'REJECTED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            
            # بودجه
            {'entity_type': 'BUDGET', 'action': 'CREATED', 'priority': 'MEDIUM', 'channel': 'IN_APP'},
            {'entity_type': 'BUDGET', 'action': 'UPDATED', 'priority': 'LOW', 'channel': 'IN_APP'},
            {'entity_type': 'BUDGET', 'action': 'APPROVED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'BUDGET', 'action': 'REJECTED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            
            # دستور پرداخت
            {'entity_type': 'PAYMENTORDER', 'action': 'CREATED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'PAYMENTORDER', 'action': 'UPDATED', 'priority': 'MEDIUM', 'channel': 'IN_APP'},
            {'entity_type': 'PAYMENTORDER', 'action': 'APPROVED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'PAYMENTORDER', 'action': 'REJECTED', 'priority': 'HIGH', 'channel': 'IN_APP'},
            {'entity_type': 'PAYMENTORDER', 'action': 'PAID', 'priority': 'HIGH', 'channel': 'IN_APP'},
            
            # سیستم
            {'entity_type': 'SYSTEM', 'action': 'CREATED', 'priority': 'LOW', 'channel': 'IN_APP'},
            {'entity_type': 'SYSTEM', 'action': 'UPDATED', 'priority': 'LOW', 'channel': 'IN_APP'},
            {'entity_type': 'SYSTEM', 'action': 'ERROR', 'priority': 'ERROR', 'channel': 'IN_APP'},
        ]
        
        created_rules = 0
        
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
            
            created_rules += 1
            print(f"   ✅ قانون ایجاد شد: {rule}")
        
        print(f"\n🎉 {created_rules} قانون اعلان ایجاد شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد قوانین اعلان: {e}")
        return False

def test_notification_system():
    """تست سیستم اعلان‌ها"""
    print("\n🧪 تست سیستم اعلان‌ها...")
    
    try:
        # یافتن admin کاربر
        admin_users = CustomUser.objects.filter(is_staff=True, is_active=True)
        if not admin_users.exists():
            print("❌ هیچ کاربر admin یافت نشد!")
            return False
        
        admin_user = admin_users.first()
        
        # تست ارسال اعلان
        send_notification(
            sender=None,
            users=[admin_user],
            verb='TEST',
            description='🧪 تست سیستم اعلان‌ها - همه چیز کار می‌کند',
            entity_type='SYSTEM',
            priority='MEDIUM'
        )
        
        print("   ✅ اعلان تستی ارسال شد")
        
        # آمار اعلان‌ها
        total_notifications = admin_user.notifications.count()
        unread_notifications = admin_user.notifications.filter(unread=True).count()
        
        print(f"   📊 آمار اعلان‌ها: {total_notifications} کل، {unread_notifications} خوانده‌نشده")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست سیستم: {e}")
        return False

def main():
    """تابع اصلی"""
    print("🔔 راه‌اندازی سیستم اعلان‌ها برای عملیات‌های مختلف")
    print("=" * 60)
    
    try:
        # راه‌اندازی سیگنال‌ها
        setup_tankhah_notifications()
        setup_factor_notifications()
        setup_budget_notifications()
        setup_payment_order_notifications()
        setup_user_notifications()
        
        # ایجاد قوانین اعلان
        create_notification_rules()
        
        # تست سیستم
        test_notification_system()
        
        print(f"\n🎉 سیستم اعلان‌ها برای عملیات‌های مختلف فعال شد!")
        print(f"\n📋 عملیات‌های پشتیبانی شده:")
        print(f"   - ایجاد/به‌روزرسانی تنخواه")
        print(f"   - ایجاد/به‌روزرسانی فاکتور")
        print(f"   - ایجاد/به‌روزرسانی تراکنش بودجه")
        print(f"   - ایجاد/به‌روزرسانی دستور پرداخت")
        print(f"   - ایجاد کاربر جدید")
        
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
