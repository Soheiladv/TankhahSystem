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
    check_budget_status,
    get_budget_status,
    get_locked_amount,
    get_warning_amount,
    calculate_allocation_percentages,
    can_delete_budget,
    get_returned_budgets,
    calculate_balance_from_transactions,
    get_committed_budget,
    get_available_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class UtilityCalculationsAPI(APIView):
    """API برای توابع کمکی محاسبات بودجه"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        اجرای توابع کمکی محاسبات بودجه
        
        Parameters:
            function_name (str): نام تابع
            parameters (dict): پارامترهای تابع
        
        Returns:
            Response: نتیجه اجرای تابع
        """
        try:
            function_name = request.data.get('function_name')
            parameters = request.data.get('parameters', {})
            
            if not function_name:
                return Response({
                    'error': _('نام تابع الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = {}
            
            if function_name == 'check_budget_status':
                obj_id = parameters.get('obj_id')
                obj_type = parameters.get('obj_type')
                filters = parameters.get('filters', {})
                
                if not obj_id or not obj_type:
                    return Response({
                        'error': _('شناسه و نوع موجودیت الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if obj_type == 'project':
                    from core.models import Project
                    obj = Project.objects.get(pk=obj_id)
                elif obj_type == 'subproject':
                    from core.models import SubProject
                    obj = SubProject.objects.get(pk=obj_id)
                elif obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    obj = Tankhah.objects.get(pk=obj_id)
                else:
                    return Response({
                        'error': _('نوع موجودیت نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                result['budget_status'] = check_budget_status(obj, filters)
            
            elif function_name == 'get_budget_status':
                entity_id = parameters.get('entity_id')
                entity_type = parameters.get('entity_type')
                filters = parameters.get('filters', {})
                
                if not entity_id or not entity_type:
                    return Response({
                        'error': _('شناسه و نوع موجودیت الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if entity_type == 'project':
                    from core.models import Project
                    entity = Project.objects.get(pk=entity_id)
                elif entity_type == 'subproject':
                    from core.models import SubProject
                    entity = SubProject.objects.get(pk=entity_id)
                elif entity_type == 'tankhah':
                    from tankhah.models import Tankhah
                    entity = Tankhah.objects.get(pk=entity_id)
                else:
                    return Response({
                        'error': _('نوع موجودیت نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                result['budget_status'] = get_budget_status(entity, filters)
            
            elif function_name == 'get_locked_amount':
                obj_id = parameters.get('obj_id')
                obj_type = parameters.get('obj_type')
                
                if not obj_id or not obj_type:
                    return Response({
                        'error': _('شناسه و نوع موجودیت الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if obj_type == 'project':
                    from core.models import Project
                    obj = Project.objects.get(pk=obj_id)
                elif obj_type == 'subproject':
                    from core.models import SubProject
                    obj = SubProject.objects.get(pk=obj_id)
                elif obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    obj = Tankhah.objects.get(pk=obj_id)
                else:
                    return Response({
                        'error': _('نوع موجودیت نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                locked_amount = get_locked_amount(obj)
                result['locked_amount'] = float(locked_amount)
                result['locked_amount_str'] = decimal_to_clean_str(locked_amount)
            
            elif function_name == 'get_warning_amount':
                obj_id = parameters.get('obj_id')
                obj_type = parameters.get('obj_type')
                
                if not obj_id or not obj_type:
                    return Response({
                        'error': _('شناسه و نوع موجودیت الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if obj_type == 'project':
                    from core.models import Project
                    obj = Project.objects.get(pk=obj_id)
                elif obj_type == 'subproject':
                    from core.models import SubProject
                    obj = SubProject.objects.get(pk=obj_id)
                elif obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    obj = Tankhah.objects.get(pk=obj_id)
                else:
                    return Response({
                        'error': _('نوع موجودیت نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                warning_amount = get_warning_amount(obj)
                result['warning_amount'] = float(warning_amount)
                result['warning_amount_str'] = decimal_to_clean_str(warning_amount)
            
            elif function_name == 'can_delete_budget':
                entity_id = parameters.get('entity_id')
                entity_type = parameters.get('entity_type')
                
                if not entity_id or not entity_type:
                    return Response({
                        'error': _('شناسه و نوع موجودیت الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if entity_type == 'project':
                    from core.models import Project
                    entity = Project.objects.get(pk=entity_id)
                elif entity_type == 'subproject':
                    from core.models import SubProject
                    entity = SubProject.objects.get(pk=entity_id)
                elif entity_type == 'tankhah':
                    from tankhah.models import Tankhah
                    entity = Tankhah.objects.get(pk=entity_id)
                else:
                    return Response({
                        'error': _('نوع موجودیت نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                can_delete = can_delete_budget(entity)
                result['can_delete'] = can_delete
            
            elif function_name == 'get_returned_budgets':
                budget_period_id = parameters.get('budget_period_id')
                entity_type = parameters.get('entity_type', 'all')
                
                if not budget_period_id:
                    return Response({
                        'error': _('شناسه دوره بودجه الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                from budgets.models import BudgetPeriod
                budget_period = BudgetPeriod.objects.get(pk=budget_period_id)
                
                returned_budgets = get_returned_budgets(budget_period, entity_type)
                result['returned_budgets'] = returned_budgets
            
            elif function_name == 'calculate_balance_from_transactions':
                budget_source_obj_id = parameters.get('budget_source_obj_id')
                budget_source_obj_type = parameters.get('budget_source_obj_type')
                
                if not budget_source_obj_id or not budget_source_obj_type:
                    return Response({
                        'error': _('شناسه و نوع منبع بودجه الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if budget_source_obj_type == 'project':
                    from core.models import Project
                    budget_source_obj = Project.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'subproject':
                    from core.models import SubProject
                    budget_source_obj = SubProject.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    budget_source_obj = Tankhah.objects.get(pk=budget_source_obj_id)
                else:
                    return Response({
                        'error': _('نوع منبع بودجه نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                balance = calculate_balance_from_transactions(budget_source_obj)
                result['balance'] = float(balance)
                result['balance_str'] = decimal_to_clean_str(balance)
            
            elif function_name == 'get_committed_budget':
                budget_source_obj_id = parameters.get('budget_source_obj_id')
                budget_source_obj_type = parameters.get('budget_source_obj_type')
                
                if not budget_source_obj_id or not budget_source_obj_type:
                    return Response({
                        'error': _('شناسه و نوع منبع بودجه الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if budget_source_obj_type == 'project':
                    from core.models import Project
                    budget_source_obj = Project.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'subproject':
                    from core.models import SubProject
                    budget_source_obj = SubProject.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    budget_source_obj = Tankhah.objects.get(pk=budget_source_obj_id)
                else:
                    return Response({
                        'error': _('نوع منبع بودجه نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                committed_budget = get_committed_budget(budget_source_obj)
                result['committed_budget'] = float(committed_budget)
                result['committed_budget_str'] = decimal_to_clean_str(committed_budget)
            
            elif function_name == 'get_available_budget':
                budget_source_obj_id = parameters.get('budget_source_obj_id')
                budget_source_obj_type = parameters.get('budget_source_obj_type')
                
                if not budget_source_obj_id or not budget_source_obj_type:
                    return Response({
                        'error': _('شناسه و نوع منبع بودجه الزامی است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # دریافت موجودیت بر اساس نوع
                if budget_source_obj_type == 'project':
                    from core.models import Project
                    budget_source_obj = Project.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'subproject':
                    from core.models import SubProject
                    budget_source_obj = SubProject.objects.get(pk=budget_source_obj_id)
                elif budget_source_obj_type == 'tankhah':
                    from tankhah.models import Tankhah
                    budget_source_obj = Tankhah.objects.get(pk=budget_source_obj_id)
                else:
                    return Response({
                        'error': _('نوع منبع بودجه نامعتبر است')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                available_budget = get_available_budget(budget_source_obj)
                result['available_budget'] = float(available_budget)
                result['available_budget_str'] = decimal_to_clean_str(available_budget)
            
            else:
                return Response({
                    'error': _('نام تابع نامعتبر است'),
                    'available_functions': [
                        'check_budget_status',
                        'get_budget_status',
                        'get_locked_amount',
                        'get_warning_amount',
                        'can_delete_budget',
                        'get_returned_budgets',
                        'calculate_balance_from_transactions',
                        'get_committed_budget',
                        'get_available_budget'
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'function_name': function_name,
                'parameters': parameters,
                'result': result
            })
            
        except ObjectDoesNotExist as e:
            return Response({
                'error': _('موجودیت یافت نشد'),
                'details': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in utility calculations: {str(e)}")
            return Response({
                'error': _('خطا در اجرای تابع کمکی'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست توابع کمکی موجود
        
        Returns:
            Response: لیست توابع کمکی
        """
        functions = {
            'check_budget_status': {
                'description': 'بررسی وضعیت بودجه',
                'parameters': ['obj_id', 'obj_type', 'filters']
            },
            'get_budget_status': {
                'description': 'دریافت وضعیت بودجه',
                'parameters': ['entity_id', 'entity_type', 'filters']
            },
            'get_locked_amount': {
                'description': 'محاسبه مبلغ قفل‌شده',
                'parameters': ['obj_id', 'obj_type']
            },
            'get_warning_amount': {
                'description': 'محاسبه مبلغ هشدار',
                'parameters': ['obj_id', 'obj_type']
            },
            'can_delete_budget': {
                'description': 'بررسی امکان حذف بودجه',
                'parameters': ['entity_id', 'entity_type']
            },
            'get_returned_budgets': {
                'description': 'دریافت بودجه‌های برگشتی',
                'parameters': ['budget_period_id', 'entity_type']
            },
            'calculate_balance_from_transactions': {
                'description': 'محاسبه مانده از تراکنش‌ها',
                'parameters': ['budget_source_obj_id', 'budget_source_obj_type']
            },
            'get_committed_budget': {
                'description': 'محاسبه بودجه در تعهد',
                'parameters': ['budget_source_obj_id', 'budget_source_obj_type']
            },
            'get_available_budget': {
                'description': 'محاسبه بودجه در دسترس',
                'parameters': ['budget_source_obj_id', 'budget_source_obj_type']
            }
        }
        
        return Response({
            'functions': functions,
            'total_functions': len(functions)
        })
