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
    get_factor_total_budget,
    get_factor_used_budget,
    get_factor_remaining_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class FactorCalculationsAPI(APIView):
    """API برای محاسبات بودجه فاکتور"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه فاکتور
        
        Parameters:
            factor_id (int): شناسه فاکتور
            calculation_type (str): نوع محاسبه (total, used, remaining, all)
            filters (dict): فیلترهای اضافی
        
        Returns:
            Response: نتیجه محاسبه
        """
        try:
            factor_id = request.data.get('factor_id')
            calculation_type = request.data.get('calculation_type', 'all')
            filters = request.data.get('filters', {})
            
            if not factor_id:
                return Response({
                    'error': _('شناسه فاکتور الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from tankhah.models import Factor
            factor = Factor.objects.get(pk=factor_id)
            
            result = {}
            
            if calculation_type in ['total', 'all']:
                result['total_budget'] = float(get_factor_total_budget(factor, filters))
            
            if calculation_type in ['used', 'all']:
                result['used_budget'] = float(get_factor_used_budget(factor, filters))
            
            if calculation_type in ['remaining', 'all']:
                result['remaining_budget'] = float(get_factor_remaining_budget(factor, filters))
            
            # تبدیل به رشته تمیز
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    result[f'{key}_str'] = decimal_to_clean_str(Decimal(str(value)))
            
            return Response({
                'factor_id': factor_id,
                'factor_name': factor.number if hasattr(factor, 'number') else f'Factor {factor_id}',
                'calculation_type': calculation_type,
                'filters': filters,
                'result': result
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('فاکتور یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in factor calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه فاکتور'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست فاکتورها برای محاسبه بودجه
        
        Returns:
            Response: لیست فاکتورها
        """
        try:
            from tankhah.models import Factor
            
            factors = Factor.objects.all().values('id', 'number')
            
            return Response({
                'factors': list(factors),
                'total_count': len(factors)
            })
            
        except Exception as e:
            logger.error(f"Error getting factors: {str(e)}")
            return Response({
                'error': _('خطا در دریافت لیست فاکتورها'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
