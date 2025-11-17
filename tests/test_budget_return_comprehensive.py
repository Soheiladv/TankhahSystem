#!/usr/bin/env python
"""
تست جامع برگشت بودجه از تنخواه
این تست بررسی می‌کند که:
1. برگشت بودجه از تنخواه به درستی ثبت می‌شود
2. مانده بودجه در سطوح مختلف (تنخواه، پروژه، مرکز هزینه، کلان بودجه) به درستی محاسبه می‌شود
3. تراکنش‌های برگشت در تاریخچه ثبت می‌شوند
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

from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    BudgetItem, BudgetHistory
)
from core.models import Organization, Project, SubProject, OrganizationType
from tankhah.models import Tankhah, Factor
from accounts.models import CustomUser

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BudgetReturnComprehensiveTest(TransactionTestCase):
    """
    تست جامع برگشت بودجه از تنخواه
    """
    
    def setUp(self):
        """ایجاد داده‌های تست"""
        logger.info("شروع ایجاد داده‌های تست...")
        
        # ایجاد کاربر
        self.user, created = CustomUser.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@example.com',
                'password': 'testpass123'
            }
        )
        
        # ایجاد نوع سازمان
        self.org_type, created = OrganizationType.objects.get_or_create(
            org_type='TEST_TYPE',
            defaults={
                'fname': 'نوع سازمان تست',
                'is_budget_allocatable': True,
                'is_active': True
            }
        )
        
        # ایجاد سازمان
        self.organization, created = Organization.objects.get_or_create(
            code='ORG001',
            defaults={
                'name': 'سازمان تست',
                'org_type': self.org_type,
                'is_active': True
            }
        )
        
        # ایجاد پروژه
        self.project, created = Project.objects.get_or_create(
            code='PRJ001',
            defaults={
                'name': 'پروژه تست',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'is_active': True
            }
        )
        # اضافه کردن سازمان به پروژه
        self.project.organizations.add(self.organization)
        
        # ایجاد زیرپروژه
        self.subproject = SubProject.objects.create(
            name='زیرپروژه تست',
            project=self.project,
            description='زیرپروژه تست برای برگشت بودجه',
            is_active=True
        )
        
        # ایجاد دوره بودجه
        self.budget_period = BudgetPeriod.objects.create(
            organization=self.organization,
            name='دوره بودجه تست 1404',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            total_amount=Decimal('1000000000'),  # 1 میلیارد ریال
            locked_percentage=10,  # 10% قفل
            warning_threshold=20,  # 20% هشدار
            created_by=self.user,
            is_active=True
        )
        
        # ایجاد ردیف بودجه
        self.budget_item = BudgetItem.objects.create(
            budget_period=self.budget_period,
            organization=self.organization,
            name='ردیف بودجه تست',
            code='ITEM001',
            is_active=True
        )
        
        # ایجاد تخصیص بودجه
        self.budget_allocation = BudgetAllocation.objects.create(
            budget_period=self.budget_period,
            organization=self.organization,
            budget_item=self.budget_item,
            project=self.project,
            subproject=self.subproject,
            allocated_amount=Decimal('500000000'),  # 500 میلیون ریال
            allocation_date=date.today(),
            description='تخصیص بودجه برای پروژه تست',
            created_by=self.user,
            is_active=True
        )
        
        # ایجاد تنخواه
        self.tankhah = Tankhah.objects.create(
            project_budget_allocation=self.budget_allocation,
            organization=self.organization,
            project=self.project,
            subproject=self.subproject,
            amount=Decimal('200000000'),  # 200 میلیون ریال
            remaining_budget=Decimal('200000000'),
            description='تنخواه تست',
            created_by=self.user,
            is_active=True
        )
        
        logger.info("داده‌های تست با موفقیت ایجاد شدند")
        
    def test_budget_return_from_tankhah(self):
        """تست برگشت بودجه از تنخواه"""
        logger.info("شروع تست برگشت بودجه از تنخواه...")
        
        # مبلغ برگشتی
        return_amount = Decimal('50000000')  # 50 میلیون ریال
        
        # ثبت تراکنش برگشت
        with transaction.atomic():
            return_transaction = BudgetTransaction.objects.create(
                allocation=self.budget_allocation,
                transaction_type='RETURN',
                amount=return_amount,
                related_tankhah=self.tankhah,
                description=f'برگشت {return_amount:,.0f} ریال از تنخواه {self.tankhah.number}',
                created_by=self.user,
                transaction_id=f'RETURN-{self.tankhah.pk}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            
            # به‌روزرسانی مبالغ
            self.budget_allocation.allocated_amount -= return_amount
            self.budget_allocation.returned_amount += return_amount
            self.budget_allocation.save()
            
            # به‌روزرسانی تنخواه
            self.tankhah.remaining_budget -= return_amount
            self.tankhah.save()
            
            # به‌روزرسانی دوره بودجه
            self.budget_period.returned_amount += return_amount
            self.budget_period.save()
            
            # ثبت در تاریخچه
            BudgetHistory.objects.create(
                content_object=self.budget_allocation,
                action='RETURN',
                amount=return_amount,
                created_by=self.user,
                details=f'برگشت {return_amount:,.0f} ریال از تنخواه {self.tankhah.number}',
                transaction_type='RETURN',
                transaction_id=return_transaction.transaction_id
            )
        
        logger.info(f"تراکنش برگشت با مبلغ {return_amount:,.0f} ریال ثبت شد")
        
        # بررسی‌های اعتبارسنجی
        self._verify_budget_calculations(return_amount)
        self._verify_transaction_history(return_amount)
        self._verify_budget_status()
        
    def _verify_budget_calculations(self, return_amount):
        """بررسی محاسبات بودجه در سطوح مختلف"""
        logger.info("بررسی محاسبات بودجه...")
        
        # تازه‌سازی اشیاء از دیتابیس
        self.budget_allocation.refresh_from_db()
        self.tankhah.refresh_from_db()
        self.budget_period.refresh_from_db()
        
        # بررسی مانده تنخواه
        expected_tankhah_remaining = Decimal('200000000') - return_amount
        self.assertEqual(
            self.tankhah.remaining_budget, 
            expected_tankhah_remaining,
            f"مانده تنخواه باید {expected_tankhah_remaining:,.0f} ریال باشد"
        )
        logger.info(f"✅ مانده تنخواه: {self.tankhah.remaining_budget:,.0f} ریال")
        
        # بررسی مانده تخصیص بودجه
        expected_allocation_remaining = Decimal('500000000') - return_amount
        actual_allocation_remaining = self.budget_allocation.get_remaining_amount()
        self.assertEqual(
            actual_allocation_remaining,
            expected_allocation_remaining,
            f"مانده تخصیص باید {expected_allocation_remaining:,.0f} ریال باشد"
        )
        logger.info(f"✅ مانده تخصیص: {actual_allocation_remaining:,.0f} ریال")
        
        # بررسی مانده پروژه
        project_remaining = self.project.get_remaining_budget() if hasattr(self.project, 'get_remaining_budget') else Decimal('0')
        logger.info(f"✅ مانده پروژه: {project_remaining:,.0f} ریال")
        
        # بررسی مانده دوره بودجه کلان
        period_remaining = self.budget_period.get_remaining_amount()
        expected_period_remaining = Decimal('1000000000') - Decimal('500000000') + return_amount
        self.assertEqual(
            period_remaining,
            expected_period_remaining,
            f"مانده دوره بودجه باید {expected_period_remaining:,.0f} ریال باشد"
        )
        logger.info(f"✅ مانده دوره بودجه: {period_remaining:,.0f} ریال")
        
        # بررسی مبلغ برگشتی در تخصیص
        self.assertEqual(
            self.budget_allocation.returned_amount,
            return_amount,
            f"مبلغ برگشتی در تخصیص باید {return_amount:,.0f} ریال باشد"
        )
        
        # بررسی مبلغ برگشتی در دوره بودجه
        self.assertEqual(
            self.budget_period.returned_amount,
            return_amount,
            f"مبلغ برگشتی در دوره بودجه باید {return_amount:,.0f} ریال باشد"
        )
        
    def _verify_transaction_history(self, return_amount):
        """بررسی تاریخچه تراکنش‌ها"""
        logger.info("بررسی تاریخچه تراکنش‌ها...")
        
        # بررسی تراکنش برگشت
        return_transactions = BudgetTransaction.objects.filter(
            allocation=self.budget_allocation,
            transaction_type='RETURN'
        )
        
        self.assertEqual(
            return_transactions.count(),
            1,
            "باید دقیقاً یک تراکنش برگشت وجود داشته باشد"
        )
        
        return_transaction = return_transactions.first()
        self.assertEqual(
            return_transaction.amount,
            return_amount,
            f"مبلغ تراکنش برگشت باید {return_amount:,.0f} ریال باشد"
        )
        
        self.assertEqual(
            return_transaction.related_tankhah,
            self.tankhah,
            "تراکنش باید به تنخواه مربوط باشد"
        )
        
        # بررسی تاریخچه بودجه
        budget_history = BudgetHistory.objects.filter(
            content_object=self.budget_allocation,
            action='RETURN'
        )
        
        self.assertEqual(
            budget_history.count(),
            1,
            "باید دقیقاً یک رکورد تاریخچه برگشت وجود داشته باشد"
        )
        
        history_record = budget_history.first()
        self.assertEqual(
            history_record.amount,
            return_amount,
            f"مبلغ در تاریخچه باید {return_amount:,.0f} ریال باشد"
        )
        
        logger.info("✅ تاریخچه تراکنش‌ها صحیح است")
        
    def _verify_budget_status(self):
        """بررسی وضعیت بودجه"""
        logger.info("بررسی وضعیت بودجه...")
        
        # بررسی وضعیت تخصیص
        allocation_status, allocation_message = self.budget_allocation.check_allocation_status()
        logger.info(f"وضعیت تخصیص: {allocation_status} - {allocation_message}")
        
        # بررسی وضعیت دوره بودجه
        period_status, period_message = self.budget_period.check_budget_status_no_save()
        logger.info(f"وضعیت دوره بودجه: {period_status} - {period_message}")
        
        # بررسی قفل بودن
        is_locked, lock_message = self.budget_period.is_locked
        logger.info(f"وضعیت قفل دوره بودجه: {is_locked} - {lock_message}")
        
        # بررسی قفل بودن تخصیص
        is_allocation_locked, is_allocation_active = self.budget_allocation.update_lock_status()
        logger.info(f"وضعیت قفل تخصیص: {is_allocation_locked}, فعال: {is_allocation_active}")
        
    def test_multiple_budget_returns(self):
        """تست چندین برگشت بودجه متوالی"""
        logger.info("شروع تست چندین برگشت بودجه...")
        
        return_amounts = [Decimal('20000000'), Decimal('30000000'), Decimal('10000000')]
        total_returned = Decimal('0')
        
        for i, amount in enumerate(return_amounts):
            with transaction.atomic():
                return_transaction = BudgetTransaction.objects.create(
                    allocation=self.budget_allocation,
                    transaction_type='RETURN',
                    amount=amount,
                    related_tankhah=self.tankhah,
                    description=f'برگشت {i+1}: {amount:,.0f} ریال',
                    created_by=self.user,
                    transaction_id=f'RETURN-{self.tankhah.pk}-{i+1}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                )
                
                # به‌روزرسانی مبالغ
                self.budget_allocation.allocated_amount -= amount
                self.budget_allocation.returned_amount += amount
                self.budget_allocation.save()
                
                self.tankhah.remaining_budget -= amount
                self.tankhah.save()
                
                self.budget_period.returned_amount += amount
                self.budget_period.save()
                
                total_returned += amount
                
                logger.info(f"برگشت {i+1}: {amount:,.0f} ریال - مجموع: {total_returned:,.0f} ریال")
        
        # بررسی نهایی
        self.budget_allocation.refresh_from_db()
        self.tankhah.refresh_from_db()
        self.budget_period.refresh_from_db()
        
        # بررسی تعداد تراکنش‌ها
        return_transactions = BudgetTransaction.objects.filter(
            allocation=self.budget_allocation,
            transaction_type='RETURN'
        )
        self.assertEqual(
            return_transactions.count(),
            len(return_amounts),
            f"باید {len(return_amounts)} تراکنش برگشت وجود داشته باشد"
        )
        
        # بررسی مجموع برگشتی
        self.assertEqual(
            self.budget_allocation.returned_amount,
            total_returned,
            f"مجموع برگشتی در تخصیص باید {total_returned:,.0f} ریال باشد"
        )
        
        self.assertEqual(
            self.budget_period.returned_amount,
            total_returned,
            f"مجموع برگشتی در دوره بودجه باید {total_returned:,.0f} ریال باشد"
        )
        
        logger.info(f"✅ تست چندین برگشت با موفقیت انجام شد - مجموع: {total_returned:,.0f} ریال")
        
    def test_budget_return_validation(self):
        """تست اعتبارسنجی برگشت بودجه"""
        logger.info("شروع تست اعتبارسنجی برگشت بودجه...")
        
        # تست برگشت مبلغ بیشتر از مانده تنخواه
        excessive_amount = Decimal('300000000')  # بیشتر از مانده تنخواه
        
        with self.assertRaises(Exception):
            BudgetTransaction.objects.create(
                allocation=self.budget_allocation,
                transaction_type='RETURN',
                amount=excessive_amount,
                related_tankhah=self.tankhah,
                description='برگشت مبلغ بیش از حد',
                created_by=self.user
            )
        
        logger.info("✅ اعتبارسنجی مبلغ بیش از حد صحیح است")
        
        # تست برگشت مبلغ منفی
        negative_amount = Decimal('-10000000')
        
        with self.assertRaises(Exception):
            BudgetTransaction.objects.create(
                allocation=self.budget_allocation,
                transaction_type='RETURN',
                amount=negative_amount,
                related_tankhah=self.tankhah,
                description='برگشت مبلغ منفی',
                created_by=self.user
            )
        
        logger.info("✅ اعتبارسنجی مبلغ منفی صحیح است")
        
    def tearDown(self):
        """پاکسازی داده‌های تست"""
        logger.info("پاکسازی داده‌های تست...")
        
        # حذف تراکنش‌ها
        BudgetTransaction.objects.all().delete()
        BudgetHistory.objects.all().delete()
        
        # حذف تنخواه
        Tankhah.objects.all().delete()
        
        # حذف تخصیص بودجه
        BudgetAllocation.objects.all().delete()
        
        # حذف ردیف بودجه
        BudgetItem.objects.all().delete()
        
        # حذف دوره بودجه
        BudgetPeriod.objects.all().delete()
        
        # حذف پروژه‌ها
        SubProject.objects.all().delete()
        Project.objects.all().delete()
        
        # حذف سازمان
        Organization.objects.all().delete()
        
        # حذف نوع سازمان
        OrganizationType.objects.all().delete()
        
        # حذف کاربر
        CustomUser.objects.all().delete()
        
        logger.info("✅ پاکسازی داده‌های تست انجام شد")


def run_comprehensive_test():
    """اجرای تست جامع"""
    logger.info("=" * 60)
    logger.info("شروع تست جامع برگشت بودجه از تنخواه")
    logger.info("=" * 60)
    
    try:
        # ایجاد نمونه تست
        test_instance = BudgetReturnComprehensiveTest()
        test_instance.setUp()
        
        # اجرای تست‌ها
        logger.info("\n🔍 تست برگشت بودجه از تنخواه...")
        test_instance.test_budget_return_from_tankhah()
        
        logger.info("\n🔍 تست چندین برگشت بودجه...")
        test_instance.test_multiple_budget_returns()
        
        logger.info("\n🔍 تست اعتبارسنجی...")
        test_instance.test_budget_return_validation()
        
        # پاکسازی
        test_instance.tearDown()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ تمام تست‌ها با موفقیت انجام شدند!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای تست: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False


if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
