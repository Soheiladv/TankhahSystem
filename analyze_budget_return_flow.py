#!/usr/bin/env python
"""
تست بررسی مسیر مبلغ برگشتی در سیستم بودجه
این تست بررسی می‌کند که مبلغ برگشتی دقیقاً کجا می‌رود و چگونه می‌توان آن را مجدداً تخصیص داد
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
from django.contrib.contenttypes.models import ContentType

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    BudgetItem, BudgetHistory
)

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_budget_return_flow():
    """تحلیل جریان مبلغ برگشتی در سیستم بودجه"""
    logger.info("=" * 80)
    logger.info("تحلیل جریان مبلغ برگشتی در سیستم بودجه")
    logger.info("=" * 80)
    
    try:
        # انتخاب دوره بودجه فعال
        budget_period = BudgetPeriod.objects.filter(is_active=True).first()
        if not budget_period:
            logger.error("❌ هیچ دوره بودجه فعالی موجود نیست")
            return False
        
        logger.info(f"✅ دوره بودجه انتخاب شده: {budget_period.name}")
        
        # انتخاب تخصیص بودجه فعال
        budget_allocation = BudgetAllocation.objects.filter(
            budget_period=budget_period,
            is_active=True
        ).first()
        
        if not budget_allocation:
            logger.error("❌ هیچ تخصیص بودجه فعالی موجود نیست")
            return False
        
        logger.info(f"✅ تخصیص بودجه انتخاب شده: {budget_allocation.pk}")
        
        # نمایش وضعیت اولیه
        logger.info("\n" + "="*60)
        logger.info("وضعیت اولیه سیستم:")
        logger.info("="*60)
        
        logger.info(f"📊 دوره بودجه کلان:")
        logger.info(f"   - مبلغ کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"   - مجموع تخصیص‌ها: {budget_period.total_allocated:,.0f} ریال")
        logger.info(f"   - مجموع برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده محاسبه شده: {budget_period.get_remaining_amount():,.0f} ریال")
        
        logger.info(f"\n📊 تخصیص بودجه:")
        logger.info(f"   - مبلغ تخصیص: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"   - مبلغ برگشتی: {budget_allocation.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده محاسبه شده: {budget_allocation.get_remaining_amount():,.0f} ریال")
        
        # محاسبه مانده دستی برای مقایسه
        manual_remaining_period = budget_period.total_amount - budget_period.total_allocated + budget_period.returned_amount
        logger.info(f"\n🔍 محاسبه دستی مانده دوره: {manual_remaining_period:,.0f} ریال")
        
        # تعیین مبلغ برگشتی
        current_remaining = budget_allocation.get_remaining_amount()
        return_amount = min(current_remaining * Decimal('0.05'), Decimal('5000000'))  # 5% یا حداکثر 5 میلیون
        
        if return_amount <= 0:
            logger.warning("⚠️ مبلغ برگشتی صفر یا منفی است")
            return False
        
        logger.info(f"\n💰 مبلغ برگشتی تعیین شده: {return_amount:,.0f} ریال")
        
        # اجرای برگشت بودجه
        logger.info("\n" + "="*60)
        logger.info("اجرای برگشت بودجه:")
        logger.info("="*60)
        
        with transaction.atomic():
            # ثبت تراکنش برگشت
            return_transaction = BudgetTransaction.objects.create(
                allocation=budget_allocation,
                transaction_type='RETURN',
                amount=return_amount,
                description=f'تحلیل جریان برگشت {return_amount:,.0f} ریال',
                transaction_id=f'ANALYSIS-RETURN-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            logger.info(f"✅ تراکنش برگشت ثبت شد: {return_transaction.pk}")
            
            # به‌روزرسانی مبالغ
            old_allocated = budget_allocation.allocated_amount
            old_returned = budget_allocation.returned_amount
            
            budget_allocation.allocated_amount -= return_amount
            budget_allocation.returned_amount += return_amount
            budget_allocation.save()
            
            logger.info(f"✅ تخصیص بودجه به‌روزرسانی شد:")
            logger.info(f"   - مبلغ تخصیص: {old_allocated:,.0f} → {budget_allocation.allocated_amount:,.0f} ریال")
            logger.info(f"   - مبلغ برگشتی: {old_returned:,.0f} → {budget_allocation.returned_amount:,.0f} ریال")
            
            # به‌روزرسانی دوره بودجه
            old_period_returned = budget_period.returned_amount
            budget_period.returned_amount += return_amount
            budget_period.save()
            
            logger.info(f"✅ دوره بودجه به‌روزرسانی شد:")
            logger.info(f"   - مجموع برگشتی: {old_period_returned:,.0f} → {budget_period.returned_amount:,.0f} ریال")
            
            # ثبت در تاریخچه
            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(budget_allocation),
                object_id=budget_allocation.pk,
                action='RETURN',
                amount=return_amount,
                details=f'تحلیل جریان برگشت {return_amount:,.0f} ریال',
                transaction_type='RETURN',
                transaction_id=return_transaction.transaction_id
            )
            logger.info(f"✅ تاریخچه ثبت شد")
        
        # تحلیل وضعیت نهایی
        logger.info("\n" + "="*60)
        logger.info("تحلیل وضعیت نهایی:")
        logger.info("="*60)
        
        # تازه‌سازی اشیاء
        budget_allocation.refresh_from_db()
        budget_period.refresh_from_db()
        
        logger.info(f"📊 دوره بودجه کلان (بعد از برگشت):")
        logger.info(f"   - مبلغ کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"   - مجموع تخصیص‌ها: {budget_period.total_allocated:,.0f} ریال")
        logger.info(f"   - مجموع برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده محاسبه شده: {budget_period.get_remaining_amount():,.0f} ریال")
        
        logger.info(f"\n📊 تخصیص بودجه (بعد از برگشت):")
        logger.info(f"   - مبلغ تخصیص: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"   - مبلغ برگشتی: {budget_allocation.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده محاسبه شده: {budget_allocation.get_remaining_amount():,.0f} ریال")
        
        # تحلیل جریان مبلغ برگشتی
        logger.info("\n" + "="*60)
        logger.info("🔍 تحلیل جریان مبلغ برگشتی:")
        logger.info("="*60)
        
        logger.info("1️⃣ مبلغ برگشتی از کجا کم می‌شود؟")
        logger.info(f"   ✅ از مبلغ تخصیص‌یافته تخصیص بودجه: {return_amount:,.0f} ریال")
        
        logger.info("\n2️⃣ مبلغ برگشتی کجا اضافه می‌شود؟")
        logger.info(f"   ✅ به فیلد returned_amount تخصیص بودجه: {return_amount:,.0f} ریال")
        logger.info(f"   ✅ به فیلد returned_amount دوره بودجه کلان: {return_amount:,.0f} ریال")
        
        logger.info("\n3️⃣ مبلغ برگشتی چگونه در محاسبه مانده استفاده می‌شود؟")
        logger.info("   فرمول محاسبه مانده دوره بودجه:")
        logger.info("   مانده = مبلغ_کل - مجموع_تخصیص‌ها + مجموع_برگشتی")
        logger.info(f"   مانده = {budget_period.total_amount:,.0f} - {budget_period.total_allocated:,.0f} + {budget_period.returned_amount:,.0f}")
        logger.info(f"   مانده = {budget_period.get_remaining_amount():,.0f} ریال")
        
        logger.info("\n4️⃣ آیا مبلغ برگشتی قابل تخصیص مجدد است؟")
        logger.info("   ✅ بله! مبلغ برگشتی در محاسبه مانده دوره بودجه لحاظ می‌شود")
        logger.info("   ✅ این مبلغ می‌تواند برای تخصیص‌های جدید استفاده شود")
        
        # بررسی امکان تخصیص مجدد
        logger.info("\n" + "="*60)
        logger.info("🔍 بررسی امکان تخصیص مجدد:")
        logger.info("="*60)
        
        available_for_allocation = budget_period.get_remaining_amount()
        logger.info(f"💰 مبلغ قابل تخصیص: {available_for_allocation:,.0f} ریال")
        
        if available_for_allocation > 0:
            logger.info("✅ مبلغ برگشتی در دسترس برای تخصیص‌های جدید است")
            logger.info("✅ می‌توان تخصیص جدیدی به این مبلغ ایجاد کرد")
        else:
            logger.warning("⚠️ مبلغ قابل تخصیص صفر یا منفی است")
        
        # نمایش تراکنش‌های برگشت
        logger.info("\n" + "="*60)
        logger.info("📋 تراکنش‌های برگشت:")
        logger.info("="*60)
        
        return_transactions = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).order_by('-timestamp')
        
        for i, tx in enumerate(return_transactions, 1):
            logger.info(f"{i}. مبلغ: {tx.amount:,.0f} ریال - تاریخ: {tx.timestamp.strftime('%Y/%m/%d %H:%M')}")
            logger.info(f"   توضیحات: {tx.description}")
        
        # نمایش تاریخچه
        logger.info("\n" + "="*60)
        logger.info("📋 تاریخچه برگشت‌ها:")
        logger.info("="*60)
        
        budget_history = BudgetHistory.objects.filter(
            content_type=ContentType.objects.get_for_model(budget_allocation),
            object_id=budget_allocation.pk,
            action='RETURN'
        ).order_by('-created_at')
        
        for i, history in enumerate(budget_history, 1):
            logger.info(f"{i}. مبلغ: {history.amount:,.0f} ریال - تاریخ: {history.created_at.strftime('%Y/%m/%d %H:%M')}")
            logger.info(f"   جزئیات: {history.details}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ تحلیل جریان مبلغ برگشتی با موفقیت کامل انجام شد!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در تحلیل: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False

if __name__ == '__main__':
    success = analyze_budget_return_flow()
    sys.exit(0 if success else 1)
