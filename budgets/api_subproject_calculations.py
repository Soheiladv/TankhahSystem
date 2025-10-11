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
    get_subproject_total_budget,
    get_subproject_used_budget,
    get_subproject_remaining_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class SubProjectCalculationsAPI(APIView):
    """API برای محاسبات بودجه زیرپروژه"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه زیرپروژه
        
        Parameters:
            subproject_id (int): شناسه زیرپروژه
            calculation_type (str): نوع محاسبه (total, used, remaining, all)
            force_refresh (bool): اجبار به‌روزرسانی کش
            filters (dict): فیلترهای اضافی
        
        Returns:
            Response: نتیجه محاسبه
        """
        try:
            subproject_id = request.data.get('subproject_id')
            calculation_type = request.data.get('calculation_type', 'all')
            force_refresh = request.data.get('force_refresh', False)
            filters = request.data.get('filters', {})
            
            if not subproject_id:
                return Response({
                    'error': _('شناسه زیرپروژه الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from core.models import SubProject
            subproject = SubProject.objects.get(pk=subproject_id)
            
            result = {}
            
            if calculation_type in ['total', 'all']:
                result['total_budget'] = float(get_subproject_total_budget(subproject, force_refresh, filters))
            
            if calculation_type in ['used', 'all']:
                result['used_budget'] = float(get_subproject_used_budget(subproject, filters))
            
            if calculation_type in ['remaining', 'all']:
                result['remaining_budget'] = float(get_subproject_remaining_budget(subproject, force_refresh, filters))
            
            # تبدیل به رشته تمیز
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    result[f'{key}_str'] = decimal_to_clean_str(Decimal(str(value)))
            
            return Response({
                'subproject_id': subproject_id,
                'subproject_name': subproject.name,
                'calculation_type': calculation_type,
                'force_refresh': force_refresh,
                'filters': filters,
                'result': result
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('زیرپروژه یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in subproject calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه زیرپروژه'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست زیرپروژه‌ها برای محاسبه بودجه
        
        Returns:
            Response: لیست زیرپروژه‌ها
        """
        try:
            from core.models import SubProject
            
            subprojects = SubProject.objects.all().values('id', 'name')
            
            return Response({
                'subprojects': list(subprojects),
                'total_count': len(subprojects)
            })
            
        except Exception as e:
            logger.error(f"Error getting subprojects: {str(e)}")
            return Response({
                'error': _('خطا در دریافت لیست زیرپروژه‌ها'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
