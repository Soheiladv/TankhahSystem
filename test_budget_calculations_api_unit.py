#!/usr/bin/env python
"""
تست‌های واحد برای API های محاسباتی بودجه
این فایل شامل تست‌های متمرکز بر روی توابع محاسباتی است.
"""

import os
import sys
import django
from decimal import Decimal
from unittest.mock import patch, MagicMock

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from budgets.budget_calculations import (
    calculate_remaining_amount,
    calculate_threshold_amount,
    decimal_to_clean_str
)

User = get_user_model()

class BudgetCalculationsUnitTest(TestCase):
    """تست‌های واحد برای توابع محاسباتی"""
    
    def test_calculate_threshold_amount(self):
        """تست محاسبه مبلغ بر اساس درصد"""
        # تست درصد 10
        result = calculate_threshold_amount(Decimal('1000000'), Decimal('10'))
        expected = Decimal('100000')
        self.assertEqual(result, expected)
        
        # تست درصد 50
        result = calculate_threshold_amount(Decimal('2000000'), Decimal('50'))
        expected = Decimal('1000000')
        self.assertEqual(result, expected)
        
        # تست درصد 0
        result = calculate_threshold_amount(Decimal('1000000'), Decimal('0'))
        expected = Decimal('0')
        self.assertEqual(result, expected)
        
        # تست درصد 100
        result = calculate_threshold_amount(Decimal('1000000'), Decimal('100'))
        expected = Decimal('1000000')
        self.assertEqual(result, expected)
    
    def test_decimal_to_clean_str(self):
        """تست تبدیل اعشار به رشته تمیز"""
        # تست اعداد عادی
        result = decimal_to_clean_str(Decimal('1000000'))
        self.assertEqual(result, '1,000,000')
        
        # تست اعداد اعشاری
        result = decimal_to_clean_str(Decimal('1000000.50'))
        self.assertEqual(result, '1,000,000.50')
        
        # تست اعداد کوچک
        result = decimal_to_clean_str(Decimal('100'))
        self.assertEqual(result, '100')
        
        # تست صفر
        result = decimal_to_clean_str(Decimal('0'))
        self.assertEqual(result, '0')
        
        # تست اعداد منفی
        result = decimal_to_clean_str(Decimal('-1000000'))
        self.assertEqual(result, '-1,000,000')

class APIIntegrationTest(APITestCase):
    """تست‌های یکپارچگی API"""
    
    def setUp(self):
        """تنظیم داده‌های تست"""
        try:
            self.user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            try:
                self.user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            except Exception as e:
                # اگر کاربر با ایمیل مشابه وجود دارد، آن را حذف و دوباره ایجاد کن
                try:
                    existing_user = User.objects.get(email='test@example.com')
                    existing_user.delete()
                    self.user = User.objects.create_user(
                        username='testuser',
                        email='test@example.com',
                        password='testpass123'
                    )
                except:
                    # اگر همچنان مشکل داشت، از ایمیل متفاوت استفاده کن
                    import time
                    self.user = User.objects.create_user(
                        username='testuser',
                        email=f'test_{int(time.time())}@example.com',
                        password='testpass123'
                    )
        self.client = Client(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)
    
    def test_calculations_overview_structure(self):
        """تست ساختار پاسخ نمای کلی API"""
        url = reverse('budget_calculations_overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # بررسی کلیدهای اصلی
        required_keys = ['message', 'functions', 'total_functions', 'api_endpoints']
        for key in required_keys:
            self.assertIn(key, data)
        
        # بررسی ساختار functions
        functions = data['functions']
        expected_categories = [
            'allocation_calculations',
            'organization_calculations',
            'project_calculations',
            'subproject_calculations',
            'tankhah_calculations',
            'factor_calculations',
            'utility_calculations'
        ]
        for category in expected_categories:
            self.assertIn(category, functions)
        
        # بررسی ساختار api_endpoints
        api_endpoints = data['api_endpoints']
        expected_endpoints = [
            'allocation', 'organization', 'project', 'subproject',
            'tankhah', 'factor', 'utility', 'batch'
        ]
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, api_endpoints)
    
    def test_allocation_calculations_threshold(self):
        """تست محاسبه مبلغ بر اساس درصد در API"""
        url = reverse('budget_allocation_calculations')
        params = {
            'base_amount': '1000000',
            'percentage': '15'
        }
        
        with patch('budgets.api_allocation_calculations.calculate_threshold_amount') as mock_calc:
            mock_calc.return_value = Decimal('150000')
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            
            # بررسی ساختار پاسخ
            expected_keys = ['base_amount', 'percentage', 'threshold_amount', 'threshold_amount_str']
            for key in expected_keys:
                self.assertIn(key, data)
            
            # بررسی مقادیر
            self.assertEqual(data['base_amount'], 1000000.0)
            self.assertEqual(data['percentage'], 15.0)
            self.assertEqual(data['threshold_amount'], 150000.0)
            self.assertEqual(data['threshold_amount_str'], '150,000')
    
    def test_error_handling_missing_parameters(self):
        """تست مدیریت خطا برای پارامترهای مفقود"""
        url = reverse('budget_allocation_calculations')
        
        # تست بدون پارامترها
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('مبلغ پایه و درصد الزامی است', data['error'])
    
    def test_error_handling_invalid_parameters(self):
        """تست مدیریت خطا برای پارامترهای نامعتبر"""
        url = reverse('budget_allocation_calculations')
        params = {
            'base_amount': 'invalid',
            'percentage': 'invalid'
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('details', data)

class MockDataTest(APITestCase):
    """تست‌های با داده‌های Mock"""
    
    def setUp(self):
        """تنظیم داده‌های تست"""
        try:
            self.user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            try:
                self.user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            except Exception as e:
                # اگر کاربر با ایمیل مشابه وجود دارد، آن را حذف و دوباره ایجاد کن
                try:
                    existing_user = User.objects.get(email='test@example.com')
                    existing_user.delete()
                    self.user = User.objects.create_user(
                        username='testuser',
                        email='test@example.com',
                        password='testpass123'
                    )
                except:
                    # اگر همچنان مشکل داشت، از ایمیل متفاوت استفاده کن
                    import time
                    self.user = User.objects.create_user(
                        username='testuser',
                        email=f'test_{int(time.time())}@example.com',
                        password='testpass123'
                    )
        self.client = Client(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)
    
    def test_organization_calculations_with_mock(self):
        """تست محاسبات بودجه سازمان با Mock"""
        url = reverse('budget_organization_calculations')
        data = {
            'organization_id': 1,
            'calculation_type': 'all',
            'filters': {}
        }
        
        with patch('budgets.api_organization_calculations.get_organization_total_budget') as mock_total, \
             patch('budgets.api_organization_calculations.get_organization_budget') as mock_budget, \
             patch('budgets.api_organization_calculations.get_organization_remaining_budget') as mock_remaining, \
             patch('budgets.api_organization_calculations.Organization') as mock_org:
            
            # تنظیم Mock ها
            mock_org.objects.get.return_value = MagicMock(id=1, name='سازمان تست')
            mock_total.return_value = Decimal('100000000')
            mock_budget.return_value = Decimal('80000000')
            mock_remaining.return_value = Decimal('20000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            # بررسی ساختار پاسخ
            self.assertIn('organization_id', response_data)
            self.assertIn('organization_name', response_data)
            self.assertIn('calculation_type', response_data)
            self.assertIn('result', response_data)
            
            # بررسی مقادیر
            result = response_data['result']
            self.assertEqual(result['total_budget'], 100000000.0)
            self.assertEqual(result['budget'], 80000000.0)
            self.assertEqual(result['remaining_budget'], 20000000.0)
    
    def test_project_calculations_with_mock(self):
        """تست محاسبات بودجه پروژه با Mock"""
        url = reverse('budget_project_calculations')
        data = {
            'project_id': 1,
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        with patch('budgets.api_project_calculations.get_project_total_budget') as mock_total, \
             patch('budgets.api_project_calculations.get_project_used_budget') as mock_used, \
             patch('budgets.api_project_calculations.get_project_remaining_budget') as mock_remaining, \
             patch('budgets.api_project_calculations.Project') as mock_project:
            
            # تنظیم Mock ها
            mock_project.objects.get.return_value = MagicMock(id=1, name='پروژه تست')
            mock_total.return_value = Decimal('200000000')
            mock_used.return_value = Decimal('50000000')
            mock_remaining.return_value = Decimal('150000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            # بررسی ساختار پاسخ
            self.assertIn('project_id', response_data)
            self.assertIn('project_name', response_data)
            self.assertIn('calculation_type', response_data)
            self.assertIn('result', response_data)
            
            # بررسی مقادیر
            result = response_data['result']
            self.assertEqual(result['total_budget'], 200000000.0)
            self.assertEqual(result['used_budget'], 50000000.0)
            self.assertEqual(result['remaining_budget'], 150000000.0)
    
    def test_tankhah_calculations_with_mock(self):
        """تست محاسبات بودجه تنخواه با Mock"""
        url = reverse('budget_tankhah_calculations')
        data = {
            'tankhah_id': 1,
            'calculation_type': 'all',
            'filters': {}
        }
        
        with patch('budgets.api_tankhah_calculations.get_tankhah_total_budget') as mock_total, \
             patch('budgets.api_tankhah_calculations.get_tankhah_remaining_budget') as mock_remaining, \
             patch('budgets.api_tankhah_calculations.get_tankhah_committed_budget') as mock_committed, \
             patch('budgets.api_tankhah_calculations.get_tankhah_used_budget') as mock_used, \
             patch('budgets.api_tankhah_calculations.get_tankhah_available_budget') as mock_available, \
             patch('budgets.api_tankhah_calculations.check_tankhah_lock_status') as mock_lock, \
             patch('budgets.api_tankhah_calculations.Tankhah') as mock_tankhah:
            
            # تنظیم Mock ها
            mock_tankhah.objects.get.return_value = MagicMock(id=1, name='تنخواه تست')
            mock_total.return_value = Decimal('50000000')
            mock_remaining.return_value = Decimal('20000000')
            mock_committed.return_value = Decimal('10000000')
            mock_used.return_value = Decimal('20000000')
            mock_available.return_value = Decimal('30000000')
            mock_lock.return_value = False
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            # بررسی ساختار پاسخ
            self.assertIn('tankhah_id', response_data)
            self.assertIn('tankhah_name', response_data)
            self.assertIn('calculation_type', response_data)
            self.assertIn('result', response_data)
            
            # بررسی مقادیر
            result = response_data['result']
            self.assertEqual(result['total_budget'], 50000000.0)
            self.assertEqual(result['remaining_budget'], 20000000.0)
            self.assertEqual(result['committed_budget'], 10000000.0)
            self.assertEqual(result['used_budget'], 20000000.0)
            self.assertEqual(result['available_budget'], 30000000.0)
            self.assertEqual(result['lock_status'], False)
    
    def test_batch_calculations_with_mock(self):
        """تست محاسبات دسته‌ای با Mock"""
        url = reverse('budget_batch_calculations')
        data = {
            'calculations': [
                {
                    'type': 'allocation',
                    'parameters': {
                        'allocation_id': 1
                    }
                },
                {
                    'type': 'project',
                    'parameters': {
                        'project_id': 1
                    }
                }
            ]
        }
        
        with patch('budgets.api_batch_calculations.calculate_remaining_amount') as mock_alloc, \
             patch('budgets.api_batch_calculations.get_project_total_budget') as mock_proj_total, \
             patch('budgets.api_batch_calculations.get_project_used_budget') as mock_proj_used, \
             patch('budgets.api_batch_calculations.get_project_remaining_budget') as mock_proj_remaining, \
             patch('budgets.api_batch_calculations.BudgetAllocation') as mock_alloc_model, \
             patch('budgets.api_batch_calculations.Project') as mock_project:
            
            # تنظیم Mock ها
            mock_alloc_model.objects.get.return_value = MagicMock()
            mock_project.objects.get.return_value = MagicMock()
            mock_alloc.return_value = Decimal('50000000')
            mock_proj_total.return_value = Decimal('100000000')
            mock_proj_used.return_value = Decimal('30000000')
            mock_proj_remaining.return_value = Decimal('70000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            # بررسی ساختار پاسخ
            self.assertIn('total_calculations', response_data)
            self.assertIn('successful_calculations', response_data)
            self.assertIn('failed_calculations', response_data)
            self.assertIn('results', response_data)
            
            # بررسی مقادیر
            self.assertEqual(response_data['total_calculations'], 2)
            self.assertEqual(response_data['successful_calculations'], 2)
            self.assertEqual(response_data['failed_calculations'], 0)
            self.assertEqual(len(response_data['results']), 2)

class PerformanceTest(APITestCase):
    """تست‌های عملکرد"""
    
    def setUp(self):
        """تنظیم داده‌های تست"""
        try:
            self.user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            try:
                self.user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            except Exception as e:
                # اگر کاربر با ایمیل مشابه وجود دارد، آن را حذف و دوباره ایجاد کن
                try:
                    existing_user = User.objects.get(email='test@example.com')
                    existing_user.delete()
                    self.user = User.objects.create_user(
                        username='testuser',
                        email='test@example.com',
                        password='testpass123'
                    )
                except:
                    # اگر همچنان مشکل داشت، از ایمیل متفاوت استفاده کن
                    import time
                    self.user = User.objects.create_user(
                        username='testuser',
                        email=f'test_{int(time.time())}@example.com',
                        password='testpass123'
                    )
        self.client = Client(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)
    
    def test_calculation_performance(self):
        """تست عملکرد محاسبات"""
        import time
        
        url = reverse('budget_calculations_overview')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # بررسی اینکه پاسخ در زمان معقول دریافت شود (کمتر از 1 ثانیه)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)
        
        print(f"زمان اجرای نمای کلی API: {execution_time:.3f} ثانیه")

def run_unit_tests():
    """اجرای تست‌های واحد"""
    import unittest
    
    # ایجاد Test Suite
    test_suite = unittest.TestSuite()
    
    # اضافه کردن تست‌ها
    test_classes = [
        BudgetCalculationsUnitTest,
        APIIntegrationTest,
        MockDataTest,
        PerformanceTest
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # اجرای تست‌ها
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result

if __name__ == '__main__':
    result = run_unit_tests()
    
    if result.wasSuccessful():
        print("\n🎉 تمام تست‌های واحد با موفقیت انجام شد!")
    else:
        print(f"\n❌ {len(result.failures)} تست ناموفق بود.")
        print(f"❌ {len(result.errors)} خطا رخ داد.")
