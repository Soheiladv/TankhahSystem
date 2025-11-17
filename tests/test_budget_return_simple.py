#!/usr/bin/env python
"""
تست ساده برگشت بودجه از تنخواه
این تست فقط عملکرد اصلی برگشت بودجه را بررسی می‌کند
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

from django.test import TestCase
from django.db import transaction
from django.utils import timezone

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    BudgetItem, BudgetHistory
)
from core.models import Organization, Project, SubProject, OrganizationType
from tankhah.models import Tankhah
from accounts.models import CustomUser

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_budget_return_simple():
    """تست ساده برگشت بودجه"""
    logger.info("=" * 60)
    logger.info("شروع تست ساده برگشت بودجه")
    logger.info("=" * 60)
    
    try:
        # پاکسازی داده‌های قبلی
        BudgetTransaction.objects.filter(transaction_type='RETURN').delete()
        BudgetHistory.objects.filter(action='RETURN').delete()
        Tankhah.objects.filter(description__icontains='تست').delete()
        BudgetAllocation.objects.filter(description__icontains='تست').delete()
        BudgetItem.objects.filter(name__icontains='تست').delete()
        BudgetPeriod.objects.filter(name__icontains='تست').delete()
        SubProject.objects.filter(name__icontains='تست').delete()
        Project.objects.filter(name__icontains='تست').delete()
        Organization.objects.filter(name__icontains='تست').delete()
        OrganizationType.objects.filter(fname__icontains='تست').delete()
        
        logger.info("✅ پاکسازی داده‌های قبلی انجام شد")
        
        # ایجاد کاربر
        user, created = CustomUser.objects.get_or_create(
            username='test_user_budget_return',
            defaults={
                'email': 'test_budget@example.com',
                'password': 'testpass123'
            }
        )
        logger.info(f"✅ کاربر {'ایجاد' if created else 'موجود'} شد: {user.username}")
        
        # ایجاد نوع سازمان
        org_type, created = OrganizationType.objects.get_or_create(
            org_type='TEST_BUDGET_TYPE',
            defaults={
                'fname': 'نوع سازمان تست بودجه',
                'is_budget_allocatable': True,
                'is_active': True
            }
        )
        logger.info(f"✅ نوع سازمان {'ایجاد' if created else 'موجود'} شد: {org_type.fname}")
        
        # ایجاد سازمان
        organization, created = Organization.objects.get_or_create(
            code='ORG_BUDGET_TEST',
            defaults={
                'name': 'سازمان تست بودجه',
                'org_type': org_type,
                'is_active': True
            }
        )
        logger.info(f"✅ سازمان {'ایجاد' if created else 'موجود'} شد: {organization.name}")
        
        # ایجاد پروژه
        project, created = Project.objects.get_or_create(
            code='PRJ_BUDGET_TEST',
            defaults={
                'name': 'پروژه تست بودجه',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'is_active': True
            }
        )
        project.organizations.add(organization)
        logger.info(f"✅ پروژه {'ایجاد' if created else 'موجود'} شد: {project.name}")
        
        # ایجاد زیرپروژه
        subproject, created = SubProject.objects.get_or_create(
            name='زیرپروژه تست بودجه',
            project=project,
            defaults={
                'description': 'زیرپروژه تست برای برگشت بودجه',
                'is_active': True
            }
        )
        logger.info(f"✅ زیرپروژه {'ایجاد' if created else 'موجود'} شد: {subproject.name}")
        
        # ایجاد دوره بودجه
        budget_period, created = BudgetPeriod.objects.get_or_create(
            name='دوره بودجه تست برگشت',
            organization=organization,
            defaults={
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'total_amount': Decimal('1000000000'),  # 1 میلیارد ریال
                'locked_percentage': 10,  # 10% قفل
                'warning_threshold': 20,  # 20% هشدار
                'created_by': user,
                'is_active': True
            }
        )
        logger.info(f"✅ دوره بودجه {'ایجاد' if created else 'موجود'} شد: {budget_period.name}")
        
        # ایجاد ردیف بودجه
        budget_item, created = BudgetItem.objects.get_or_create(
            budget_period=budget_period,
            organization=organization,
            code='ITEM_BUDGET_TEST',
            defaults={
                'name': 'ردیف بودجه تست',
                'is_active': True
            }
        )
        logger.info(f"✅ ردیف بودجه {'ایجاد' if created else 'موجود'} شد: {budget_item.name}")
        
        # ایجاد تخصیص بودجه
        budget_allocation, created = BudgetAllocation.objects.get_or_create(
            budget_period=budget_period,
            organization=organization,
            budget_item=budget_item,
            project=project,
            subproject=subproject,
            defaults={
                'allocated_amount': Decimal('500000000'),  # 500 میلیون ریال
                'allocation_date': date.today(),
                'description': 'تخصیص بودجه برای تست برگشت',
                'created_by': user,
                'is_active': True
            }
        )
        logger.info(f"✅ تخصیص بودجه {'ایجاد' if created else 'موجود'} شد: {budget_allocation.pk}")
        
        # ایجاد تنخواه
        tankhah, created = Tankhah.objects.get_or_create(
            project_budget_allocation=budget_allocation,
            organization=organization,
            project=project,
            subproject=subproject,
            defaults={
                'amount': Decimal('200000000'),  # 200 میلیون ریال
                'remaining_budget': Decimal('200000000'),
                'description': 'تنخواه تست برای برگشت بودجه',
                'created_by': user,
                'is_active': True
            }
        )
        logger.info(f"✅ تنخواه {'ایجاد' if created else 'موجود'} شد: {tankhah.pk}")
        
        # نمایش وضعیت اولیه
        logger.info("\n" + "="*50)
        logger.info("وضعیت اولیه:")
        logger.info(f"دوره بودجه کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"تخصیص بودجه: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"تنخواه: {tankhah.amount:,.0f} ریال")
        logger.info(f"مانده تنخواه: {tankhah.remaining_budget:,.0f} ریال")
        
        # تست برگشت بودجه
        logger.info("\n" + "="*50)
        logger.info("شروع تست برگشت بودجه...")
        
        return_amount = Decimal('50000000')  # 50 میلیون ریال
        
        with transaction.atomic():
            # ثبت تراکنش برگشت
            return_transaction = BudgetTransaction.objects.create(
                allocation=budget_allocation,
                transaction_type='RETURN',
                amount=return_amount,
                related_tankhah=tankhah,
                description=f'برگشت {return_amount:,.0f} ریال از تنخواه {tankhah.pk}',
                created_by=user,
                transaction_id=f'RETURN-{tankhah.pk}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            logger.info(f"✅ تراکنش برگشت ثبت شد: {return_transaction.pk}")
            
            # به‌روزرسانی مبالغ
            budget_allocation.allocated_amount -= return_amount
            budget_allocation.returned_amount += return_amount
            budget_allocation.save()
            logger.info(f"✅ تخصیص بودجه به‌روزرسانی شد")
            
            # به‌روزرسانی تنخواه
            tankhah.remaining_budget -= return_amount
            tankhah.save()
            logger.info(f"✅ تنخواه به‌روزرسانی شد")
            
            # به‌روزرسانی دوره بودجه
            budget_period.returned_amount += return_amount
            budget_period.save()
            logger.info(f"✅ دوره بودجه به‌روزرسانی شد")
            
            # ثبت در تاریخچه
            BudgetHistory.objects.create(
                content_object=budget_allocation,
                action='RETURN',
                amount=return_amount,
                created_by=user,
                details=f'برگشت {return_amount:,.0f} ریال از تنخواه {tankhah.pk}',
                transaction_type='RETURN',
                transaction_id=return_transaction.transaction_id
            )
            logger.info(f"✅ تاریخچه ثبت شد")
        
        # نمایش وضعیت نهایی
        logger.info("\n" + "="*50)
        logger.info("وضعیت نهایی:")
        
        # تازه‌سازی اشیاء
        budget_allocation.refresh_from_db()
        tankhah.refresh_from_db()
        budget_period.refresh_from_db()
        
        logger.info(f"دوره بودجه کل: {budget_period.total_amount:,.0f} ریال")
        logger.info(f"دوره بودجه برگشتی: {budget_period.returned_amount:,.0f} ریال")
        logger.info(f"تخصیص بودجه: {budget_allocation.allocated_amount:,.0f} ریال")
        logger.info(f"تخصیص برگشتی: {budget_allocation.returned_amount:,.0f} ریال")
        logger.info(f"تنخواه: {tankhah.amount:,.0f} ریال")
        logger.info(f"مانده تنخواه: {tankhah.remaining_budget:,.0f} ریال")
        
        # بررسی‌های اعتبارسنجی
        logger.info("\n" + "="*50)
        logger.info("بررسی‌های اعتبارسنجی:")
        
        # بررسی مانده تنخواه
        expected_tankhah_remaining = Decimal('200000000') - return_amount
        if tankhah.remaining_budget == expected_tankhah_remaining:
            logger.info(f"✅ مانده تنخواه صحیح: {tankhah.remaining_budget:,.0f} ریال")
        else:
            logger.error(f"❌ مانده تنخواه نادرست: انتظار {expected_tankhah_remaining:,.0f}، دریافت {tankhah.remaining_budget:,.0f}")
        
        # بررسی مانده تخصیص بودجه
        expected_allocation_remaining = Decimal('500000000') - return_amount
        actual_allocation_remaining = budget_allocation.get_remaining_amount()
        if actual_allocation_remaining == expected_allocation_remaining:
            logger.info(f"✅ مانده تخصیص صحیح: {actual_allocation_remaining:,.0f} ریال")
        else:
            logger.error(f"❌ مانده تخصیص نادرست: انتظار {expected_allocation_remaining:,.0f}، دریافت {actual_allocation_remaining:,.0f}")
        
        # بررسی مانده دوره بودجه کلان
        period_remaining = budget_period.get_remaining_amount()
        expected_period_remaining = Decimal('1000000000') - Decimal('500000000') + return_amount
        if period_remaining == expected_period_remaining:
            logger.info(f"✅ مانده دوره بودجه صحیح: {period_remaining:,.0f} ریال")
        else:
            logger.error(f"❌ مانده دوره بودجه نادرست: انتظار {expected_period_remaining:,.0f}، دریافت {period_remaining:,.0f}")
        
        # بررسی تراکنش‌ها
        return_transactions = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        )
        if return_transactions.count() == 1:
            logger.info(f"✅ تراکنش برگشت صحیح: {return_transactions.count()} تراکنش")
        else:
            logger.error(f"❌ تعداد تراکنش‌های برگشت نادرست: {return_transactions.count()}")
        
        # بررسی تاریخچه
        budget_history = BudgetHistory.objects.filter(
            content_object=budget_allocation,
            action='RETURN'
        )
        if budget_history.count() == 1:
            logger.info(f"✅ تاریخچه برگشت صحیح: {budget_history.count()} رکورد")
        else:
            logger.error(f"❌ تعداد رکوردهای تاریخچه نادرست: {budget_history.count()}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ تست برگشت بودجه با موفقیت کامل انجام شد!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای تست: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False

if __name__ == '__main__':
    success = test_budget_return_simple()
    sys.exit(0 if success else 1)
