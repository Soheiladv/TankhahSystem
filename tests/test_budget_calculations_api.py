import json
import pytest
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock

from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction, BudgetItem
from core.models import Organization, OrganizationType, Project, SubProject
from tankhah.models import Tankhah, Factor

User = get_user_model()

class BudgetCalculationsAPITestCase(APITestCase):
    """تست‌های جامع برای API های محاسباتی بودجه"""
    
    def setUp(self):
        """تنظیم داده‌های تست"""
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

class BudgetCalculationsOverviewAPITest(BudgetCalculationsAPITestCase):
    """تست API نمای کلی محاسبات"""
    
    def test_get_calculations_overview(self):
        """تست دریافت نمای کلی API ها"""
        url = reverse('budget_calculations_overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # بررسی وجود کلیدهای اصلی
        self.assertIn('message', data)
        self.assertIn('functions', data)
        self.assertIn('total_functions', data)
        self.assertIn('api_endpoints', data)
        
        # بررسی دسته‌بندی توابع
        functions = data['functions']
        self.assertIn('allocation_calculations', functions)
        self.assertIn('organization_calculations', functions)
        self.assertIn('project_calculations', functions)
        self.assertIn('subproject_calculations', functions)
        self.assertIn('tankhah_calculations', functions)
        self.assertIn('factor_calculations', functions)
        self.assertIn('utility_calculations', functions)
        
        # بررسی تعداد توابع
        self.assertGreater(data['total_functions'], 0)
        
        # بررسی URL های API
        api_endpoints = data['api_endpoints']
        self.assertIn('allocation', api_endpoints)
        self.assertIn('organization', api_endpoints)
        self.assertIn('project', api_endpoints)
        self.assertIn('subproject', api_endpoints)
        self.assertIn('tankhah', api_endpoints)
        self.assertIn('factor', api_endpoints)
        self.assertIn('utility', api_endpoints)
        self.assertIn('batch', api_endpoints)

class AllocationCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات تخصیص بودجه"""
    
    def test_calculate_remaining_amount_success(self):
        """تست محاسبه بودجه باقی‌مانده تخصیص - موفق"""
        url = reverse('budget_allocation_calculations')
        data = {
            'allocation_id': self.allocation.id,
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
        }
        
        with patch('budgets.api_allocation_calculations.calculate_remaining_amount') as mock_calc:
            mock_calc.return_value = Decimal('50000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['allocation_id'], self.allocation.id)
            self.assertEqual(response_data['remaining_amount'], 50000000.0)
            self.assertEqual(response_data['remaining_amount_str'], '50,000,000')
            self.assertEqual(response_data['amount_field'], 'allocated_amount')
            self.assertEqual(response_data['model_name'], 'BudgetAllocation')
    
    def test_calculate_remaining_amount_allocation_not_found(self):
        """تست محاسبه بودجه باقی‌مانده - تخصیص یافت نشد"""
        url = reverse('budget_allocation_calculations')
        data = {
            'allocation_id': 99999,  # ID نامعتبر
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())
    
    def test_calculate_remaining_amount_missing_allocation_id(self):
        """تست محاسبه بودجه باقی‌مانده - شناسه تخصیص الزامی است"""
        url = reverse('budget_allocation_calculations')
        data = {
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_calculate_threshold_amount_success(self):
        """تست محاسبه مبلغ بر اساس درصد - موفق"""
        url = reverse('budget_allocation_calculations')
        params = {
            'base_amount': '1000000',
            'percentage': '10'
        }
        
        with patch('budgets.api_allocation_calculations.calculate_threshold_amount') as mock_calc:
            mock_calc.return_value = Decimal('100000')
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['base_amount'], 1000000.0)
            self.assertEqual(response_data['percentage'], 10.0)
            self.assertEqual(response_data['threshold_amount'], 100000.0)
            self.assertEqual(response_data['threshold_amount_str'], '100,000')
    
    def test_calculate_threshold_amount_missing_parameters(self):
        """تست محاسبه مبلغ بر اساس درصد - پارامترهای الزامی"""
        url = reverse('budget_allocation_calculations')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

class OrganizationCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات بودجه سازمان"""
    
    def test_calculate_organization_budget_success(self):
        """تست محاسبه بودجه سازمان - موفق"""
        url = reverse('budget_organization_calculations')
        data = {
            'organization_id': self.organization.id,
            'calculation_type': 'all',
            'filters': {}
        }
        
        with patch('budgets.api_organization_calculations.get_organization_total_budget') as mock_total, \
             patch('budgets.api_organization_calculations.get_organization_budget') as mock_budget, \
             patch('budgets.api_organization_calculations.get_organization_remaining_budget') as mock_remaining:
            
            mock_total.return_value = Decimal('100000000')
            mock_budget.return_value = Decimal('80000000')
            mock_remaining.return_value = Decimal('20000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['organization_id'], self.organization.id)
            self.assertEqual(response_data['organization_name'], self.organization.name)
            self.assertEqual(response_data['calculation_type'], 'all')
            
            result = response_data['result']
            self.assertEqual(result['total_budget'], 100000000.0)
            self.assertEqual(result['budget'], 80000000.0)
            self.assertEqual(result['remaining_budget'], 20000000.0)
    
    def test_calculate_organization_budget_organization_not_found(self):
        """تست محاسبه بودجه سازمان - سازمان یافت نشد"""
        url = reverse('budget_organization_calculations')
        data = {
            'organization_id': 99999,  # ID نامعتبر
            'calculation_type': 'total',
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())
    
    def test_calculate_organization_budget_missing_organization_id(self):
        """تست محاسبه بودجه سازمان - شناسه سازمان الزامی است"""
        url = reverse('budget_organization_calculations')
        data = {
            'calculation_type': 'total',
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_calculate_organization_budget_invalid_calculation_type(self):
        """تست محاسبه بودجه سازمان - نوع محاسبه نامعتبر"""
        url = reverse('budget_organization_calculations')
        data = {
            'organization_id': self.organization.id,
            'calculation_type': 'invalid_type',
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_get_organizations_list(self):
        """تست دریافت لیست سازمان‌ها"""
        url = reverse('budget_organization_calculations')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('organizations', response_data)
        self.assertIn('total_count', response_data)
        self.assertGreater(response_data['total_count'], 0)

class ProjectCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات بودجه پروژه"""
    
    def test_calculate_project_budget_success(self):
        """تست محاسبه بودجه پروژه - موفق"""
        url = reverse('budget_project_calculations')
        data = {
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
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['project_id'], self.project.id)
            self.assertEqual(response_data['project_name'], self.project.name)
            self.assertEqual(response_data['calculation_type'], 'all')
            self.assertEqual(response_data['force_refresh'], False)
            
            result = response_data['result']
            self.assertEqual(result['total_budget'], 100000000.0)
            self.assertEqual(result['used_budget'], 30000000.0)
            self.assertEqual(result['remaining_budget'], 70000000.0)
    
    def test_calculate_project_budget_project_not_found(self):
        """تست محاسبه بودجه پروژه - پروژه یافت نشد"""
        url = reverse('budget_project_calculations')
        data = {
            'project_id': 99999,  # ID نامعتبر
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())
    
    def test_get_projects_list(self):
        """تست دریافت لیست پروژه‌ها"""
        url = reverse('budget_project_calculations')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('projects', response_data)
        self.assertIn('total_count', response_data)
        self.assertGreater(response_data['total_count'], 0)

class SubProjectCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات بودجه زیرپروژه"""
    
    def test_calculate_subproject_budget_success(self):
        """تست محاسبه بودجه زیرپروژه - موفق"""
        url = reverse('budget_subproject_calculations')
        data = {
            'subproject_id': self.subproject.id,
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        with patch('budgets.api_subproject_calculations.get_subproject_total_budget') as mock_total, \
             patch('budgets.api_subproject_calculations.get_subproject_used_budget') as mock_used, \
             patch('budgets.api_subproject_calculations.get_subproject_remaining_budget') as mock_remaining:
            
            mock_total.return_value = Decimal('50000000')
            mock_used.return_value = Decimal('10000000')
            mock_remaining.return_value = Decimal('40000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['subproject_id'], self.subproject.id)
            self.assertEqual(response_data['subproject_name'], self.subproject.name)
            
            result = response_data['result']
            self.assertEqual(result['total_budget'], 50000000.0)
            self.assertEqual(result['used_budget'], 10000000.0)
            self.assertEqual(result['remaining_budget'], 40000000.0)
    
    def test_calculate_subproject_budget_subproject_not_found(self):
        """تست محاسبه بودجه زیرپروژه - زیرپروژه یافت نشد"""
        url = reverse('budget_subproject_calculations')
        data = {
            'subproject_id': 99999,  # ID نامعتبر
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())

class TankhahCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات بودجه تنخواه"""
    
    def test_calculate_tankhah_budget_success(self):
        """تست محاسبه بودجه تنخواه - موفق"""
        url = reverse('budget_tankhah_calculations')
        data = {
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
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['tankhah_id'], self.tankhah.id)
            
            result = response_data['result']
            self.assertEqual(result['total_budget'], 50000000.0)
            self.assertEqual(result['remaining_budget'], 20000000.0)
            self.assertEqual(result['committed_budget'], 10000000.0)
            self.assertEqual(result['used_budget'], 20000000.0)
            self.assertEqual(result['available_budget'], 30000000.0)
            self.assertEqual(result['lock_status'], False)
    
    def test_calculate_tankhah_budget_tankhah_not_found(self):
        """تست محاسبه بودجه تنخواه - تنخواه یافت نشد"""
        url = reverse('budget_tankhah_calculations')
        data = {
            'tankhah_id': 99999,  # ID نامعتبر
            'calculation_type': 'all',
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())

class FactorCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات بودجه فاکتور"""
    
    def test_calculate_factor_budget_success(self):
        """تست محاسبه بودجه فاکتور - موفق"""
        url = reverse('budget_factor_calculations')
        data = {
            'factor_id': self.factor.id,
            'calculation_type': 'all',
            'filters': {}
        }
        
        with patch('budgets.api_factor_calculations.get_factor_total_budget') as mock_total, \
             patch('budgets.api_factor_calculations.get_factor_used_budget') as mock_used, \
             patch('budgets.api_factor_calculations.get_factor_remaining_budget') as mock_remaining:
            
            mock_total.return_value = Decimal('10000000')
            mock_used.return_value = Decimal('3000000')
            mock_remaining.return_value = Decimal('7000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['factor_id'], self.factor.id)
            
            result = response_data['result']
            self.assertEqual(result['total_budget'], 10000000.0)
            self.assertEqual(result['used_budget'], 3000000.0)
            self.assertEqual(result['remaining_budget'], 7000000.0)
    
    def test_calculate_factor_budget_factor_not_found(self):
        """تست محاسبه بودجه فاکتور - فاکتور یافت نشد"""
        url = reverse('budget_factor_calculations')
        data = {
            'factor_id': 99999,  # ID نامعتبر
            'calculation_type': 'all',
            'filters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())

class UtilityCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API توابع کمکی محاسبات"""
    
    def test_check_budget_status_success(self):
        """تست بررسی وضعیت بودجه - موفق"""
        url = reverse('budget_utility_calculations')
        data = {
            'function_name': 'check_budget_status',
            'parameters': {
                'obj_id': self.project.id,
                'obj_type': 'project',
                'filters': {}
            }
        }
        
        with patch('budgets.api_utility_calculations.check_budget_status') as mock_check:
            mock_check.return_value = {'status': 'normal', 'message': 'بودجه در وضعیت عادی است'}
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['function_name'], 'check_budget_status')
            self.assertIn('budget_status', response_data['result'])
    
    def test_get_locked_amount_success(self):
        """تست محاسبه مبلغ قفل‌شده - موفق"""
        url = reverse('budget_utility_calculations')
        data = {
            'function_name': 'get_locked_amount',
            'parameters': {
                'obj_id': self.project.id,
                'obj_type': 'project'
            }
        }
        
        with patch('budgets.api_utility_calculations.get_locked_amount') as mock_locked:
            mock_locked.return_value = Decimal('5000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            result = response_data['result']
            self.assertEqual(result['locked_amount'], 5000000.0)
            self.assertEqual(result['locked_amount_str'], '5,000,000')
    
    def test_utility_function_missing_parameters(self):
        """تست تابع کمکی - پارامترهای الزامی"""
        url = reverse('budget_utility_calculations')
        data = {
            'function_name': 'check_budget_status',
            'parameters': {
                'obj_id': self.project.id
                # obj_type حذف شده
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_utility_function_invalid_function_name(self):
        """تست تابع کمکی - نام تابع نامعتبر"""
        url = reverse('budget_utility_calculations')
        data = {
            'function_name': 'invalid_function',
            'parameters': {}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        self.assertIn('available_functions', response.json())
    
    def test_get_utility_functions_list(self):
        """تست دریافت لیست توابع کمکی"""
        url = reverse('budget_utility_calculations')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('functions', response_data)
        self.assertIn('total_functions', response_data)
        self.assertGreater(response_data['total_functions'], 0)

class BatchCalculationsAPITest(BudgetCalculationsAPITestCase):
    """تست API محاسبات دسته‌ای"""
    
    def test_batch_calculations_success(self):
        """تست محاسبات دسته‌ای - موفق"""
        url = reverse('budget_batch_calculations')
        data = {
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
            
            mock_alloc.return_value = Decimal('50000000')
            mock_proj_total.return_value = Decimal('100000000')
            mock_proj_used.return_value = Decimal('30000000')
            mock_proj_remaining.return_value = Decimal('70000000')
            mock_tankhah_total.return_value = Decimal('50000000')
            mock_tankhah_remaining.return_value = Decimal('20000000')
            mock_tankhah_available.return_value = Decimal('30000000')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            
            self.assertEqual(response_data['total_calculations'], 3)
            self.assertEqual(response_data['successful_calculations'], 3)
            self.assertEqual(response_data['failed_calculations'], 0)
            self.assertEqual(len(response_data['results']), 3)
    
    def test_batch_calculations_empty_list(self):
        """تست محاسبات دسته‌ای - لیست خالی"""
        url = reverse('budget_batch_calculations')
        data = {
            'calculations': []
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_batch_calculations_missing_calculations(self):
        """تست محاسبات دسته‌ای - لیست محاسبات الزامی است"""
        url = reverse('budget_batch_calculations')
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_get_batch_calculations_sample(self):
        """تست دریافت نمونه محاسبات دسته‌ای"""
        url = reverse('budget_batch_calculations')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('sample_calculations', response_data)
        self.assertIn('description', response_data)
        self.assertIn('usage', response_data)

class AuthenticationTest(TestCase):
    """تست احراز هویت"""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('budget_calculations_overview')
    
    def test_unauthenticated_access_denied(self):
        """تست دسترسی بدون احراز هویت - رد شود"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_access_allowed(self):
        """تست دسترسی با احراز هویت - مجاز"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ErrorHandlingTest(BudgetCalculationsAPITestCase):
    """تست مدیریت خطا"""
    
    def test_internal_server_error_handling(self):
        """تست مدیریت خطای داخلی سرور"""
        url = reverse('budget_allocation_calculations')
        data = {
            'allocation_id': self.allocation.id,
            'amount_field': 'allocated_amount',
            'model_name': 'BudgetAllocation'
        }
        
        with patch('budgets.api_allocation_calculations.calculate_remaining_amount') as mock_calc:
            mock_calc.side_effect = Exception('خطای داخلی')
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            response_data = response.json()
            
            self.assertIn('error', response_data)
            self.assertIn('details', response_data)

# تست‌های عملکرد
class PerformanceTest(BudgetCalculationsAPITestCase):
    """تست‌های عملکرد"""
    
    def test_calculation_performance(self):
        """تست عملکرد محاسبات"""
        import time
        
        url = reverse('budget_project_calculations')
        data = {
            'project_id': self.project.id,
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        
        start_time = time.time()
        response = self.client.post(url, data, format='json')
        end_time = time.time()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # بررسی اینکه محاسبه در زمان معقول انجام شود (کمتر از 5 ثانیه)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 5.0)

# تست‌های یکپارچگی
class IntegrationTest(BudgetCalculationsAPITestCase):
    """تست‌های یکپارچگی"""
    
    def test_end_to_end_calculation_flow(self):
        """تست جریان کامل محاسبه از ابتدا تا انتها"""
        # 1. دریافت نمای کلی API ها
        overview_url = reverse('budget_calculations_overview')
        overview_response = self.client.get(overview_url)
        self.assertEqual(overview_response.status_code, status.HTTP_200_OK)
        
        # 2. محاسبه بودجه پروژه
        project_url = reverse('budget_project_calculations')
        project_data = {
            'project_id': self.project.id,
            'calculation_type': 'all',
            'force_refresh': False,
            'filters': {}
        }
        project_response = self.client.post(project_url, project_data, format='json')
        self.assertEqual(project_response.status_code, status.HTTP_200_OK)
        
        # 3. محاسبه بودجه تنخواه
        tankhah_url = reverse('budget_tankhah_calculations')
        tankhah_data = {
            'tankhah_id': self.tankhah.id,
            'calculation_type': 'all',
            'filters': {}
        }
        tankhah_response = self.client.post(tankhah_url, tankhah_data, format='json')
        self.assertEqual(tankhah_response.status_code, status.HTTP_200_OK)
        
        # 4. محاسبات دسته‌ای
        batch_url = reverse('budget_batch_calculations')
        batch_data = {
            'calculations': [
                {'type': 'project', 'parameters': {'project_id': self.project.id}},
                {'type': 'tankhah', 'parameters': {'tankhah_id': self.tankhah.id}}
            ]
        }
        batch_response = self.client.post(batch_url, batch_data, format='json')
        self.assertEqual(batch_response.status_code, status.HTTP_200_OK)
        
        # بررسی نتایج
        self.assertIn('functions', overview_response.json())
        self.assertIn('result', project_response.json())
        self.assertIn('result', tankhah_response.json())
        self.assertIn('results', batch_response.json())
