from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from decimal import Decimal
import logging

from budgets.budget_calculations import (
    calculate_remaining_amount,
    calculate_threshold_amount,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class BudgetCalculationsOverviewAPI(APIView):
    """
    API نمای کلی توابع محاسباتی بودجه
    
    این API لیست تمام توابع محاسباتی موجود در budget_calculations.py را نمایش می‌دهد.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        دریافت لیست تمام توابع محاسباتی موجود
        
        Returns:
            Response: لیست توابع و توضیحات آن‌ها
        """
        functions = {
            'allocation_calculations': {
                'calculate_remaining_amount': 'محاسبه بودجه باقی‌مانده تخصیص',
                'calculate_threshold_amount': 'محاسبه مقدار بر اساس درصد',
                'check_and_update_lock': 'بررسی و به‌روزرسانی قفل تخصیص',
            },
            'organization_calculations': {
                'get_organization_total_budget': 'محاسبه بودجه کل سازمان',
                'get_organization_budget': 'محاسبه بودجه سازمان',
                'get_organization_remaining_budget': 'محاسبه بودجه باقی‌مانده سازمان',
            },
            'project_calculations': {
                'get_project_total_budget': 'محاسبه بودجه کل پروژه',
                'get_project_used_budget': 'محاسبه بودجه مصرف‌شده پروژه',
                'get_project_remaining_budget': 'محاسبه بودجه باقی‌مانده پروژه',
            },
            'subproject_calculations': {
                'get_subproject_total_budget': 'محاسبه بودجه کل زیرپروژه',
                'get_subproject_used_budget': 'محاسبه بودجه مصرف‌شده زیرپروژه',
                'get_subproject_remaining_budget': 'محاسبه بودجه باقی‌مانده زیرپروژه',
            },
            'tankhah_calculations': {
                'get_tankhah_total_budget': 'محاسبه بودجه کل تنخواه',
                'get_tankhah_remaining_budget': 'محاسبه بودجه باقی‌مانده تنخواه',
                'get_tankhah_committed_budget': 'محاسبه بودجه در تعهد تنخواه',
                'get_tankhah_used_budget': 'محاسبه بودجه مصرف‌شده تنخواه',
                'get_tankhah_available_budget': 'محاسبه بودجه در دسترس تنخواه',
                'check_tankhah_lock_status': 'بررسی وضعیت قفل تنخواه',
            },
            'factor_calculations': {
                'get_factor_total_budget': 'محاسبه بودجه کل فاکتور',
                'get_factor_used_budget': 'محاسبه بودجه مصرف‌شده فاکتور',
                'get_factor_remaining_budget': 'محاسبه بودجه باقی‌مانده فاکتور',
            },
            'utility_calculations': {
                'check_budget_status': 'بررسی وضعیت بودجه',
                'get_budget_status': 'دریافت وضعیت بودجه',
                'get_locked_amount': 'محاسبه مبلغ قفل‌شده',
                'get_warning_amount': 'محاسبه مبلغ هشدار',
                'calculate_allocation_percentages': 'محاسبه درصدهای تخصیص',
                'can_delete_budget': 'بررسی امکان حذف بودجه',
                'get_returned_budgets': 'دریافت بودجه‌های برگشتی',
                'calculate_balance_from_transactions': 'محاسبه مانده از تراکنش‌ها',
                'get_committed_budget': 'محاسبه بودجه در تعهد',
                'get_available_budget': 'محاسبه بودجه در دسترس',
                'decimal_to_clean_str': 'تبدیل اعشار به رشته تمیز',
            }
        }
        
        return Response({
            'message': _('لیست توابع محاسباتی بودجه'),
            'functions': functions,
            'total_functions': sum(len(category) for category in functions.values()),
            'api_endpoints': {
                'allocation': '/api/budget/calculations/allocation/',
                'organization': '/api/budget/calculations/organization/',
                'project': '/api/budget/calculations/project/',
                'subproject': '/api/budget/calculations/subproject/',
                'tankhah': '/api/budget/calculations/tankhah/',
                'factor': '/api/budget/calculations/factor/',
                'utility': '/api/budget/calculations/utility/',
                'batch': '/api/budget/calculations/batch/',
            }
        })

class AllocationCalculationsAPI(APIView):
    """API برای محاسبات تخصیص بودجه"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه باقی‌مانده تخصیص
        
        Parameters:
            allocation_id (int): شناسه تخصیص بودجه
            amount_field (str): نام فیلد مقدار (پیش‌فرض: 'allocated_amount')
            model_name (str): نام مدل (پیش‌فرض: 'BudgetAllocation')
        
        Returns:
            Response: مبلغ باقی‌مانده
        """
        try:
            allocation_id = request.data.get('allocation_id')
            amount_field = request.data.get('amount_field', 'allocated_amount')
            model_name = request.data.get('model_name', 'BudgetAllocation')
            
            if not allocation_id:
                return Response({
                    'error': _('شناسه تخصیص الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from budgets.models import BudgetAllocation
            allocation = BudgetAllocation.objects.get(pk=allocation_id)
            
            remaining_amount = calculate_remaining_amount(
                allocation, 
                amount_field=amount_field, 
                model_name=model_name
            )
            
            return Response({
                'allocation_id': allocation_id,
                'remaining_amount': float(remaining_amount),
                'remaining_amount_str': decimal_to_clean_str(remaining_amount),
                'amount_field': amount_field,
                'model_name': model_name
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('تخصیص بودجه یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in calculate_remaining_amount: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه باقی‌مانده'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        محاسبه مقدار بر اساس درصد
        
        Parameters:
            base_amount (float): مبلغ پایه
            percentage (float): درصد
        
        Returns:
            Response: مبلغ محاسبه شده
        """
        try:
            base_amount = request.GET.get('base_amount')
            percentage = request.GET.get('percentage')
            
            if not base_amount or not percentage:
                return Response({
                    'error': _('مبلغ پایه و درصد الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            base_amount = Decimal(str(base_amount))
            percentage = Decimal(str(percentage))
            
            threshold_amount = calculate_threshold_amount(base_amount, percentage)
            
            return Response({
                'base_amount': float(base_amount),
                'percentage': float(percentage),
                'threshold_amount': float(threshold_amount),
                'threshold_amount_str': decimal_to_clean_str(threshold_amount)
            })
            
        except Exception as e:
            logger.error(f"Error in calculate_threshold_amount: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه مبلغ بر اساس درصد'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
