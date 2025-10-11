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
    get_project_total_budget,
    get_project_used_budget,
    get_project_remaining_budget,
    get_tankhah_total_budget,
    get_tankhah_remaining_budget,
    get_tankhah_available_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class BatchCalculationsAPI(APIView):
    """API برای محاسبات دسته‌ای"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        اجرای محاسبات دسته‌ای
        
        Parameters:
            calculations (list): لیست محاسبات برای اجرا
        
        Returns:
            Response: نتایج تمام محاسبات
        """
        try:
            calculations = request.data.get('calculations', [])
            
            if not calculations:
                return Response({
                    'error': _('لیست محاسبات الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = []
            
            for calc in calculations:
                try:
                    calc_type = calc.get('type')
                    calc_params = calc.get('parameters', {})
                    
                    if calc_type == 'allocation':
                        # محاسبه تخصیص
                        allocation_id = calc_params.get('allocation_id')
                        if allocation_id:
                            from budgets.models import BudgetAllocation
                            allocation = BudgetAllocation.objects.get(pk=allocation_id)
                            remaining = calculate_remaining_amount(allocation)
                            results.append({
                                'type': 'allocation',
                                'id': allocation_id,
                                'result': {
                                    'remaining_amount': float(remaining),
                                    'remaining_amount_str': decimal_to_clean_str(remaining)
                                }
                            })
                    
                    elif calc_type == 'project':
                        # محاسبه پروژه
                        project_id = calc_params.get('project_id')
                        if project_id:
                            from core.models import Project
                            project = Project.objects.get(pk=project_id)
                            total = get_project_total_budget(project)
                            used = get_project_used_budget(project)
                            remaining = get_project_remaining_budget(project)
                            results.append({
                                'type': 'project',
                                'id': project_id,
                                'result': {
                                    'total_budget': float(total),
                                    'used_budget': float(used),
                                    'remaining_budget': float(remaining),
                                    'total_budget_str': decimal_to_clean_str(total),
                                    'used_budget_str': decimal_to_clean_str(used),
                                    'remaining_budget_str': decimal_to_clean_str(remaining)
                                }
                            })
                    
                    elif calc_type == 'tankhah':
                        # محاسبه تنخواه
                        tankhah_id = calc_params.get('tankhah_id')
                        if tankhah_id:
                            from tankhah.models import Tankhah
                            tankhah = Tankhah.objects.get(pk=tankhah_id)
                            total = get_tankhah_total_budget(tankhah)
                            remaining = get_tankhah_remaining_budget(tankhah)
                            available = get_tankhah_available_budget(tankhah)
                            results.append({
                                'type': 'tankhah',
                                'id': tankhah_id,
                                'result': {
                                    'total_budget': float(total),
                                    'remaining_budget': float(remaining),
                                    'available_budget': float(available),
                                    'total_budget_str': decimal_to_clean_str(total),
                                    'remaining_budget_str': decimal_to_clean_str(remaining),
                                    'available_budget_str': decimal_to_clean_str(available)
                                }
                            })
                    
                except Exception as e:
                    results.append({
                        'type': calc.get('type', 'unknown'),
                        'id': calc.get('parameters', {}).get('id', 'unknown'),
                        'error': str(e)
                    })
            
            return Response({
                'total_calculations': len(calculations),
                'successful_calculations': len([r for r in results if 'error' not in r]),
                'failed_calculations': len([r for r in results if 'error' in r]),
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error in batch calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبات دسته‌ای'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت نمونه محاسبات دسته‌ای
        
        Returns:
            Response: نمونه محاسبات
        """
        sample_calculations = [
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
            },
            {
                'type': 'tankhah',
                'parameters': {
                    'tankhah_id': 1
                }
            }
        ]
        
        return Response({
            'sample_calculations': sample_calculations,
            'description': _('نمونه محاسبات دسته‌ای'),
            'usage': _('برای اجرای محاسبات دسته‌ای، این نمونه را در POST request ارسال کنید')
        })
