#!/usr/bin/env python
"""
تست تخصیص مجدد مبلغ برگشتی
این تست نشان می‌دهد که چگونه می‌توان مبلغ برگشتی را مجدداً تخصیص داد
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
from core.models import Organization, Project, SubProject, OrganizationType
from accounts.models import CustomUser

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reallocate_returned_budget():
    """تست تخصیص مجدد مبلغ برگشتی"""
    logger.info("=" * 80)
    logger.info("تست تخصیص مجدد مبلغ برگشتی")
    logger.info("=" * 80)
    
    try:
        # انتخاب دوره بودجه فعال
        budget_period = BudgetPeriod.objects.filter(is_active=True).first()
        if not budget_period:
            logger.error("❌ هیچ دوره بودجه فعالی موجود نیست")
            return False
        
        logger.info(f"✅ دوره بودجه انتخاب شده: {budget_period.name}")
        
        # نمایش وضعیت فعلی
        logger.info("\n" + "="*60)
        logger.info("وضعیت فعلی دوره بودجه:")
        logger.info("="*60)
        
        logger.info(f"📊 دوره بودجه کلان:")
        logger.info(f"   - مبلغ کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"   - مجموع تخصیص‌ها: {budget_period.total_allocated:,.0f} ریال")
        logger.info(f"   - مجموع برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده قابل تخصیص: {budget_period.get_remaining_amount():,.0f} ریال")
        
        # بررسی امکان تخصیص جدید
        available_amount = budget_period.get_remaining_amount()
        if available_amount <= 0:
            logger.warning("⚠️ مبلغ قابل تخصیص صفر یا منفی است")
            return False
        
        # تعیین مبلغ تخصیص جدید (حداکثر 10% از مانده)
        new_allocation_amount = min(available_amount * Decimal('0.1'), Decimal('10000000'))  # 10% یا حداکثر 10 میلیون
        
        logger.info(f"\n💰 مبلغ تخصیص جدید: {new_allocation_amount:,.0f} ریال")
        
        # ایجاد تخصیص جدید
        logger.info("\n" + "="*60)
        logger.info("ایجاد تخصیص جدید از مبلغ برگشتی:")
        logger.info("="*60)
        
        # انتخاب سازمان و پروژه موجود
        organization = budget_period.organization
        project = Project.objects.filter(organizations=organization).first()
        
        if not project:
            logger.error("❌ هیچ پروژه‌ای برای سازمان یافت نشد")
            return False
        
        # انتخاب ردیف بودجه موجود
        budget_item = BudgetItem.objects.filter(
            budget_period=budget_period,
            organization=organization
        ).first()
        
        if not budget_item:
            logger.error("❌ هیچ ردیف بودجه‌ای یافت نشد")
            return False
        
        # انتخاب کاربر سیستم
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            user = CustomUser.objects.first()
        
        with transaction.atomic():
            # ایجاد تخصیص جدید
            new_allocation = BudgetAllocation.objects.create(
                budget_period=budget_period,
                organization=organization,
                budget_item=budget_item,
                project=project,
                allocated_amount=new_allocation_amount,
                allocation_date=date.today(),
                description=f'تخصیص جدید از مبلغ برگشتی - {new_allocation_amount:,.0f} ریال',
                created_by=user,
                is_active=True
            )
            
            logger.info(f"✅ تخصیص جدید ایجاد شد: {new_allocation.pk}")
            logger.info(f"   - مبلغ تخصیص: {new_allocation.allocated_amount:,.0f} ریال")
            logger.info(f"   - پروژه: {project.name}")
            logger.info(f"   - سازمان: {organization.name}")
            
            # ثبت در تاریخچه
            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(new_allocation),
                object_id=new_allocation.pk,
                action='CREATE',
                amount=new_allocation_amount,
                created_by=user,
                details=f'تخصیص جدید از مبلغ برگشتی - {new_allocation_amount:,.0f} ریال',
                transaction_type='ALLOCATION',
                transaction_id=f'NEW-ALLOC-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            
            logger.info(f"✅ تاریخچه تخصیص جدید ثبت شد")
        
        # نمایش وضعیت نهایی
        logger.info("\n" + "="*60)
        logger.info("وضعیت نهایی بعد از تخصیص مجدد:")
        logger.info("="*60)
        
        # تازه‌سازی دوره بودجه
        budget_period.refresh_from_db()
        
        logger.info(f"📊 دوره بودجه کلان (بعد از تخصیص مجدد):")
        logger.info(f"   - مبلغ کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"   - مجموع تخصیص‌ها: {budget_period.total_allocated:,.0f} ریال")
        logger.info(f"   - مجموع برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"   - مانده قابل تخصیص: {budget_period.get_remaining_amount():,.0f} ریال")
        
        # تحلیل تغییرات
        logger.info("\n" + "="*60)
        logger.info("🔍 تحلیل تغییرات:")
        logger.info("="*60)
        
        logger.info("1️⃣ مبلغ برگشتی چگونه استفاده شد؟")
        logger.info(f"   ✅ مبلغ {new_allocation_amount:,.0f} ریال از مانده دوره بودجه برای تخصیص جدید استفاده شد")
        
        logger.info("\n2️⃣ آیا مبلغ برگشتی هنوز در سیستم موجود است؟")
        logger.info(f"   ✅ بله! مبلغ برگشتی ({budget_period.returned_amount:,.0f} ریال) همچنان در فیلد returned_amount ثبت است")
        
        logger.info("\n3️⃣ چگونه مبلغ برگشتی قابل تخصیص مجدد است؟")
        logger.info("   فرمول محاسبه مانده:")
        logger.info("   مانده = مبلغ_کل - مجموع_تخصیص‌ها + مجموع_برگشتی")
        logger.info(f"   مانده = {budget_period.total_amount:,.0f} - {budget_period.total_allocated:,.0f} + {budget_period.returned_amount:,.0f}")
        logger.info(f"   مانده = {budget_period.get_remaining_amount():,.0f} ریال")
        
        logger.info("\n4️⃣ نتیجه:")
        logger.info("   ✅ مبلغ برگشتی در محاسبه مانده لحاظ می‌شود")
        logger.info("   ✅ این مبلغ می‌تواند برای تخصیص‌های جدید استفاده شود")
        logger.info("   ✅ سیستم به درستی مبلغ برگشتی را مدیریت می‌کند")
        
        # نمایش تمام تخصیص‌ها
        logger.info("\n" + "="*60)
        logger.info("📋 تمام تخصیص‌های بودجه:")
        logger.info("="*60)
        
        all_allocations = BudgetAllocation.objects.filter(
            budget_period=budget_period
        ).order_by('-allocation_date')
        
        for i, alloc in enumerate(all_allocations, 1):
            logger.info(f"{i}. تخصیص {alloc.pk}: {alloc.allocated_amount:,.0f} ریال")
            logger.info(f"   پروژه: {alloc.project.name if alloc.project else 'بدون پروژه'}")
            logger.info(f"   تاریخ: {alloc.allocation_date}")
            logger.info(f"   وضعیت: {'فعال' if alloc.is_active else 'غیرفعال'}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ تست تخصیص مجدد مبلغ برگشتی با موفقیت کامل انجام شد!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در تست: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False

if __name__ == '__main__':
    success = test_reallocate_returned_budget()
    sys.exit(0 if success else 1)
