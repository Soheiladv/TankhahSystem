#!/usr/bin/env python
"""
تست‌های یکپارچگی برای API های محاسباتی بودجه
این فایل شامل تست‌های کامل با داده‌های واقعی است.
"""

import os
import sys
import django
from decimal import Decimal
import json

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction, BudgetItem
from core.models import Organization, OrganizationType, Project, SubProject
from tankhah.models import Tankhah, Factor

User = get_user_model()

class BudgetCalculationsIntegrationTest(APITestCase):
    """تست‌های یکپارچگی کامل برای API های محاسباتی"""
    
    def setUp(self):
        """تنظیم داده‌های تست کامل"""
        # ایجاد کاربر
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # ایجاد نوع سازمان
        self.org_type = OrganizationType.objects.create(
            name='نوع تست',
            code='TEST_TYPE'
        )
        
        # ایجاد سازمان
        self.organization = Organization.objects.create(
            name='سازمان تست',
            code='TEST_ORG',
            org_type=self.org_type
        )
        
        # ایجاد دوره بودجه
        self.budget_period = BudgetPeriod.objects.create(
            organization=self.organization,
            name='دوره تست 1404',
            start_date='2024-01-01',
            end_date='2024-12-31',
            total_amount=Decimal('1000000000'),  # 1 میلیارد ریال
            locked_percentage=10,
            warning_threshold=20
        )
        
        # ایجاد ردیف بودجه
        self.budget_item = BudgetItem.objects.create(
            budget_period=self.budget_period,
            organization=self.organization,
            name='ردیف تست',
            code='TEST_ITEM'
        )
        
        # ایجاد پروژه
        self.project = Project.objects.create(
            name='پروژه تست',
            code='TEST_PROJECT'
        )
        self.project.organizations.add(self.organization)
        
        # ایجاد زیرپروژه
        self.subproject = SubProject.objects.create(
            name='زیرپروژه تست',
            project=self.project
        )
        
        # ایجاد تخصیص بودجه
        self.allocation = BudgetAllocation.objects.create(
            budget_period=self.budget_period,
            organization=self.organization,
            budget_item=self.budget_item,
            project=self.project,
            allocated_amount=Decimal('100000000')  # 100 میلیون ریال
        )
        
        # ایجاد تنخواه
        self.tankhah = Tankhah.objects.create(
            name='تنخواه تست',
            project=self.project
        )
        
        # ایجاد فاکتور
        self.factor = Factor.objects.create(
            name='فاکتور تست',
            tankhah=self.tankhah
        )
        
        # ایجاد تراکنش‌های بودجه
        self.create_budget_transactions()
    
    def create_budget_transactions(self):
        """ایجاد تراکنش‌های بودجه برای تست"""
        # تراکنش تخصیص
        BudgetTransaction.objects.create(
            budget_allocation=self.allocation,
            transaction_type='ALLOCATION',
            amount=Decimal('100000000'),
            description='تخصیص اولیه بودجه'
        )
        
        # تراکنش مصرف
        BudgetTransaction.objects.create(
            budget_allocation=self.allocation,
            transaction_type='CONSUMPTION',
            amount=Decimal('30000000'),
            description='مصرف بودجه'
        )
        
        # تراکنش برگشت
        BudgetTransaction.objects.create(
            budget_allocation=self.allocation,
            transaction_type='RETURN',
            amount=Decimal('10000000'),
            description='برگشت بودجه'
        )
    
    def test_complete_calculation_flow(self):
        """تست جریان کامل محاسبات"""
        print("\n🔄 تست جریان کامل محاسبات...")
        
        # 1. دریافت نمای کلی API ها
        overview_url = reverse('budget_calculations_overview')
        overview_response = self.client.get(overview_url)
        
        self.assertEqual(overview_response.status_code, status.HTTP_200_OK)
        overview_data = overview_response.json()
        self.assertIn('functions', overview_data)
        print("✅ نمای کلی API ها دریافت شد")
        
        # 2. محاسبه بودجه باقی‌مانده تخصیص
        allocation_url = reverse('budget_allocation_calculations')
        allocation_data = {
            'allocation_id': self.allocation.id,
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
        }
        
        with patch('budgets.api_allocation_calculations.calculate_remaining_amount') as mock_calc:
            mock_calc.return_value = Decimal('80000000')
            
            allocation_response = self.client.post(allocation_url, allocation_data, format='json')
            
            self.assertEqual(allocation_response.status_code, status.HTTP_200_OK)
            allocation_result = allocation_response.json()
            self.assertIn('remaining_amount', allocation_result)
            print("✅ محاسبه بودجه باقی‌مانده تخصیص انجام شد")
        
        # 3. محاسبه بودجه پروژه
        project_url = reverse('budget_project_calculations')
        project_data = {
            'project_id': self.project.id,
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        with patch('budgets.api_project_calculations.get_project_total_budget') as mock_total, \
             patch('budgets.api_project_calculations.get_project_used_budget') as mock_used, \
             patch('budgets.api_project_calculations.get_project_remaining_budget') as mock_remaining:
            
            mock_total.return_value = Decimal('100000000')
            mock_used.return_value = Decimal('30000000')
            mock_remaining.return_value = Decimal('70000000')
            
            project_response = self.client.post(project_url, project_data, format='json')
            
            self.assertEqual(project_response.status_code, status.HTTP_200_OK)
            project_result = project_response.json()
            self.assertIn('result', project_result)
            print("✅ محاسبه بودجه پروژه انجام شد")
        
        # 4. محاسبه بودجه تنخواه
        tankhah_url = reverse('budget_tankhah_calculations')
        tankhah_data = {
            'tankhah_id': self.tankhah.id,
            'calculation_type': 'all',
            'filters': {}
        }
        
        with patch('budgets.api_tankhah_calculations.get_tankhah_total_budget') as mock_total, \
             patch('budgets.api_tankhah_calculations.get_tankhah_remaining_budget') as mock_remaining, \
             patch('budgets.api_tankhah_calculations.get_tankhah_committed_budget') as mock_committed, \
             patch('budgets.api_tankhah_calculations.get_tankhah_used_budget') as mock_used, \
             patch('budgets.api_tankhah_calculations.get_tankhah_available_budget') as mock_available, \
             patch('budgets.api_tankhah_calculations.check_tankhah_lock_status') as mock_lock:
            
            mock_total.return_value = Decimal('50000000')
            mock_remaining.return_value = Decimal('20000000')
            mock_committed.return_value = Decimal('10000000')
            mock_used.return_value = Decimal('20000000')
            mock_available.return_value = Decimal('30000000')
            mock_lock.return_value = False
            
            tankhah_response = self.client.post(tankhah_url, tankhah_data, format='json')
            
            self.assertEqual(tankhah_response.status_code, status.HTTP_200_OK)
            tankhah_result = tankhah_response.json()
            self.assertIn('result', tankhah_result)
            print("✅ محاسبه بودجه تنخواه انجام شد")
        
        # 5. محاسبات دسته‌ای
        batch_url = reverse('budget_batch_calculations')
        batch_data = {
            'calculations': [
                {
                    'type': 'allocation',
                    'parameters': {
                        'allocation_id': self.allocation.id
                    }
                },
                {
                    'type': 'project',
                    'parameters': {
                        'project_id': self.project.id
                    }
                },
                {
                    'type': 'tankhah',
                    'parameters': {
                        'tankhah_id': self.tankhah.id
                    }
                }
            ]
        }
        
        with patch('budgets.api_batch_calculations.calculate_remaining_amount') as mock_alloc, \
             patch('budgets.api_batch_calculations.get_project_total_budget') as mock_proj_total, \
             patch('budgets.api_batch_calculations.get_project_used_budget') as mock_proj_used, \
             patch('budgets.api_batch_calculations.get_project_remaining_budget') as mock_proj_remaining, \
             patch('budgets.api_batch_calculations.get_tankhah_total_budget') as mock_tankhah_total, \
             patch('budgets.api_batch_calculations.get_tankhah_remaining_budget') as mock_tankhah_remaining, \
             patch('budgets.api_batch_calculations.get_tankhah_available_budget') as mock_tankhah_available:
            
            mock_alloc.return_value = Decimal('80000000')
            mock_proj_total.return_value = Decimal('100000000')
            mock_proj_used.return_value = Decimal('30000000')
            mock_proj_remaining.return_value = Decimal('70000000')
            mock_tankhah_total.return_value = Decimal('50000000')
            mock_tankhah_remaining.return_value = Decimal('20000000')
            mock_tankhah_available.return_value = Decimal('30000000')
            
            batch_response = self.client.post(batch_url, batch_data, format='json')
            
            self.assertEqual(batch_response.status_code, status.HTTP_200_OK)
            batch_result = batch_response.json()
            self.assertIn('results', batch_result)
            self.assertEqual(batch_result['total_calculations'], 3)
            print("✅ محاسبات دسته‌ای انجام شد")
        
        print("🎉 جریان کامل محاسبات با موفقیت انجام شد!")
    
    def test_error_scenarios(self):
        """تست سناریوهای خطا"""
        print("\n⚠️ تست سناریوهای خطا...")
        
        # تست شناسه نامعتبر
        project_url = reverse('budget_project_calculations')
        invalid_data = {
            'project_id': 99999,  # ID نامعتبر
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        response = self.client.post(project_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        print("✅ خطای شناسه نامعتبر مدیریت شد")
        
        # تست پارامترهای مفقود
        allocation_url = reverse('budget_allocation_calculations')
        missing_data = {
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
            # allocation_id حذف شده
        }
        
        response = self.client.post(allocation_url, missing_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        print("✅ خطای پارامترهای مفقود مدیریت شد")
        
        # تست نوع محاسبه نامعتبر
        organization_url = reverse('budget_organization_calculations')
        invalid_type_data = {
            'organization_id': self.organization.id,
            'calculation_type': 'invalid_type',
            'filters': {}
        }
        
        response = self.client.post(organization_url, invalid_type_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        print("✅ خطای نوع محاسبه نامعتبر مدیریت شد")
        
        print("🎉 تمام سناریوهای خطا با موفقیت مدیریت شدند!")
    
    def test_performance_under_load(self):
        """تست عملکرد تحت بار"""
        print("\n⚡ تست عملکرد تحت بار...")
        
        import time
        
        # تست چندین درخواست متوالی
        start_time = time.time()
        
        for i in range(10):
            overview_url = reverse('budget_calculations_overview')
            response = self.client.get(overview_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"✅ 10 درخواست متوالی در {execution_time:.3f} ثانیه انجام شد")
        print(f"✅ میانگین زمان هر درخواست: {execution_time/10:.3f} ثانیه")
        
        # بررسی اینکه زمان اجرا معقول باشد
        self.assertLess(execution_time, 5.0)  # کمتر از 5 ثانیه
    
    def test_data_consistency(self):
        """تست سازگاری داده‌ها"""
        print("\n🔍 تست سازگاری داده‌ها...")
        
        # تست دریافت لیست‌ها
        list_urls = [
            ('budget_organization_calculations', 'organizations'),
            ('budget_project_calculations', 'projects'),
            ('budget_subproject_calculations', 'subprojects'),
            ('budget_tankhah_calculations', 'tankhahs'),
            ('budget_factor_calculations', 'factors')
        ]
        
        for url_name, data_key in list_urls:
            url = reverse(url_name)
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            
            self.assertIn(data_key, data)
            self.assertIn('total_count', data)
            self.assertIsInstance(data[data_key], list)
            print(f"✅ لیست {data_key} سازگار است")
        
        print("🎉 تمام داده‌ها سازگار هستند!")
    
    def test_authentication_requirements(self):
        """تست الزامات احراز هویت"""
        print("\n🔐 تست الزامات احراز هویت...")
        
        # ایجاد کلاینت بدون احراز هویت
        unauthenticated_client = Client()
        
        # تست دسترسی بدون احراز هویت
        overview_url = reverse('budget_calculations_overview')
        response = unauthenticated_client.get(overview_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print("✅ دسترسی بدون احراز هویت رد شد")
        
        # تست دسترسی با احراز هویت
        response = self.client.get(overview_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ دسترسی با احراز هویت مجاز است")
        
        print("🎉 الزامات احراز هویت صحیح است!")

def run_integration_tests():
    """اجرای تست‌های یکپارچگی"""
    import unittest
    
    # ایجاد Test Suite
    test_suite = unittest.TestSuite()
    
    # اضافه کردن تست‌ها
    tests = unittest.TestLoader().loadTestsFromTestCase(BudgetCalculationsIntegrationTest)
    test_suite.addTests(tests)
    
    # اجرای تست‌ها
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == '__main__':
    result = run_integration_tests()
    
    if result.wasSuccessful():
        print("\n🎉 تمام تست‌های یکپارچگی با موفقیت انجام شد!")
    else:
        print(f"\n❌ {len(result.failures)} تست ناموفق بود.")
        print(f"❌ {len(result.errors)} خطا رخ داد.")
        
        # نمایش جزئیات خطاها
        for failure in result.failures:
            print(f"\n❌ تست ناموفق: {failure[0]}")
            print(f"جزئیات: {failure[1]}")
        
        for error in result.errors:
            print(f"\n❌ خطا: {error[0]}")
            print(f"جزئیات: {error[1]}")
