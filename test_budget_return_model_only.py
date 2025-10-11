#!/usr/bin/env python
"""
تست بسیار ساده برگشت بودجه
این تست فقط روی مدل‌های بودجه تمرکز می‌کند
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta
import logging

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.db import transaction
from django.utils import timezone

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    BudgetItem, BudgetHistory
)

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_budget_return_model_only():
    """تست برگشت بودجه فقط روی مدل‌ها"""
    logger.info("=" * 60)
    logger.info("شروع تست برگشت بودجه (فقط مدل‌ها)")
    logger.info("=" * 60)
    
    try:
        # بررسی وجود داده‌های موجود
        existing_periods = BudgetPeriod.objects.count()
        existing_allocations = BudgetAllocation.objects.count()
        existing_transactions = BudgetTransaction.objects.count()
        
        logger.info(f"داده‌های موجود:")
        logger.info(f"- دوره‌های بودجه: {existing_periods}")
        logger.info(f"- تخصیص‌های بودجه: {existing_allocations}")
        logger.info(f"- تراکنش‌های بودجه: {existing_transactions}")
        
        if existing_periods == 0:
            logger.warning("⚠️ هیچ دوره بودجه‌ای موجود نیست")
            return False
        
        if existing_allocations == 0:
            logger.warning("⚠️ هیچ تخصیص بودجه‌ای موجود نیست")
            return False
        
        # انتخاب اولین دوره بودجه فعال
        budget_period = BudgetPeriod.objects.filter(is_active=True).first()
        if not budget_period:
            logger.warning("⚠️ هیچ دوره بودجه فعالی موجود نیست")
            return False
        
        logger.info(f"✅ دوره بودجه انتخاب شده: {budget_period.name}")
        
        # انتخاب اولین تخصیص بودجه فعال
        budget_allocation = BudgetAllocation.objects.filter(
            budget_period=budget_period,
            is_active=True
        ).first()
        
        if not budget_allocation:
            logger.warning("⚠️ هیچ تخصیص بودجه فعالی موجود نیست")
            return False
        
        logger.info(f"✅ تخصیص بودجه انتخاب شده: {budget_allocation.pk}")
        
        # نمایش وضعیت اولیه
        logger.info("\n" + "="*50)
        logger.info("وضعیت اولیه:")
        logger.info(f"دوره بودجه کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"دوره بودجه برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"تخصیص بودجه: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"تخصیص برگشتی: {budget_allocation.returned_amount:,.0f} ریال")
        
        # محاسبه مانده فعلی
        remaining_amount = budget_allocation.get_remaining_amount()
        logger.info(f"مانده تخصیص: {remaining_amount:,.0f} ریال")
        
        # تعیین مبلغ برگشتی (حداکثر 10% از مانده)
        max_return_amount = remaining_amount * Decimal('0.1')  # 10% از مانده
        return_amount = min(max_return_amount, Decimal('1000000'))  # حداکثر 1 میلیون ریال
        
        if return_amount <= 0:
            logger.warning("⚠️ مبلغ برگشتی صفر یا منفی است")
            return False
        
        logger.info(f"مبلغ برگشتی تعیین شده: {return_amount:,.0f} ریال")
        
        # تست برگشت بودجه
        logger.info("\n" + "="*50)
        logger.info("شروع تست برگشت بودجه...")
        
        with transaction.atomic():
            # ثبت تراکنش برگشت
            return_transaction = BudgetTransaction.objects.create(
                allocation=budget_allocation,
                transaction_type='RETURN',
                amount=return_amount,
                description=f'تست برگشت {return_amount:,.0f} ریال',
                transaction_id=f'TEST-RETURN-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            logger.info(f"✅ تراکنش برگشت ثبت شد: {return_transaction.pk}")
            
            # به‌روزرسانی مبالغ
            budget_allocation.allocated_amount -= return_amount
            budget_allocation.returned_amount += return_amount
            budget_allocation.save()
            logger.info(f"✅ تخصیص بودجه به‌روزرسانی شد")
            
            # به‌روزرسانی دوره بودجه
            budget_period.returned_amount += return_amount
            budget_period.save()
            logger.info(f"✅ دوره بودجه به‌روزرسانی شد")
            
            # ثبت در تاریخچه
            from django.contrib.contenttypes.models import ContentType
            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(budget_allocation),
                object_id=budget_allocation.pk,
                action='RETURN',
                amount=return_amount,
                details=f'تست برگشت {return_amount:,.0f} ریال',
                transaction_type='RETURN',
                transaction_id=return_transaction.transaction_id
            )
            logger.info(f"✅ تاریخچه ثبت شد")
        
        # نمایش وضعیت نهایی
        logger.info("\n" + "="*50)
        logger.info("وضعیت نهایی:")
        
        # تازه‌سازی اشیاء
        budget_allocation.refresh_from_db()
        budget_period.refresh_from_db()
        
        logger.info(f"دوره بودجه کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"دوره بودجه برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"تخصیص بودجه: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"تخصیص برگشتی: {budget_allocation.returned_amount:,.0f} ریال")
        
        # بررسی‌های اعتبارسنجی
        logger.info("\n" + "="*50)
        logger.info("بررسی‌های اعتبارسنجی:")
        
        # بررسی مانده تخصیص بودجه
        new_remaining_amount = budget_allocation.get_remaining_amount()
        expected_remaining = remaining_amount - return_amount
        
        if abs(new_remaining_amount - expected_remaining) < Decimal('0.01'):
            logger.info(f"✅ مانده تخصیص صحیح: {new_remaining_amount:,.0f} ریال")
        else:
            logger.error(f"❌ مانده تخصیص نادرست: انتظار {expected_remaining:,.0f}، دریافت {new_remaining_amount:,.0f}")
        
        # بررسی مانده دوره بودجه کلان
        period_remaining = budget_period.get_remaining_amount()
        logger.info(f"✅ مانده دوره بودجه: {period_remaining:,.0f} ریال")
        
        # بررسی تراکنش‌ها
        return_transactions = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        )
        logger.info(f"✅ تراکنش‌های برگشت: {return_transactions.count()} تراکنش")
        
        # بررسی تاریخچه
        from django.contrib.contenttypes.models import ContentType
        budget_history = BudgetHistory.objects.filter(
            content_type=ContentType.objects.get_for_model(budget_allocation),
            object_id=budget_allocation.pk,
            action='RETURN'
        )
        logger.info(f"✅ رکوردهای تاریخچه: {budget_history.count()} رکورد")
        
        # بررسی وضعیت بودجه
        allocation_status, allocation_message = budget_allocation.check_allocation_status()
        logger.info(f"✅ وضعیت تخصیص: {allocation_status} - {allocation_message}")
        
        period_status, period_message = budget_period.check_budget_status_no_save()
        logger.info(f"✅ وضعیت دوره بودجه: {period_status} - {period_message}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ تست برگشت بودجه با موفقیت کامل انجام شد!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای تست: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False

if __name__ == '__main__':
    success = test_budget_return_model_only()
    sys.exit(0 if success else 1)
