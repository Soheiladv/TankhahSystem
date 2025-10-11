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
    get_tankhah_total_budget,
    get_tankhah_remaining_budget,
    get_tankhah_committed_budget,
    get_tankhah_used_budget,
    get_tankhah_available_budget,
    check_tankhah_lock_status,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class TankhahCalculationsAPI(APIView):
    """API برای محاسبات بودجه تنخواه"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه تنخواه
        
        Parameters:
            tankhah_id (int): شناسه تنخواه
            calculation_type (str): نوع محاسبه (total, remaining, committed, used, available, lock_status, all)
            filters (dict): فیلترهای اضافی
        
        Returns:
            Response: نتیجه محاسبه
        """
        try:
            tankhah_id = request.data.get('tankhah_id')
            calculation_type = request.data.get('calculation_type', 'all')
            filters = request.data.get('filters', {})
            
            if not tankhah_id:
                return Response({
                    'error': _('شناسه تنخواه الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from tankhah.models import Tankhah
            tankhah = Tankhah.objects.get(pk=tankhah_id)
            
            result = {}
            
            if calculation_type in ['total', 'all']:
                result['total_budget'] = float(get_tankhah_total_budget(tankhah, filters))
            
            if calculation_type in ['remaining', 'all']:
                result['remaining_budget'] = float(get_tankhah_remaining_budget(tankhah))
            
            if calculation_type in ['committed', 'all']:
                result['committed_budget'] = float(get_tankhah_committed_budget(tankhah))
            
            if calculation_type in ['used', 'all']:
                result['used_budget'] = float(get_tankhah_used_budget(tankhah, filters))
            
            if calculation_type in ['available', 'all']:
                result['available_budget'] = float(get_tankhah_available_budget(tankhah))
            
            if calculation_type in ['lock_status', 'all']:
                result['lock_status'] = check_tankhah_lock_status(tankhah)
            
            # تبدیل به رشته تمیز
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    result[f'{key}_str'] = decimal_to_clean_str(Decimal(str(value)))
            
            return Response({
                'tankhah_id': tankhah_id,
                'tankhah_name': tankhah.number if hasattr(tankhah, 'number') else f'Tankhah {tankhah_id}',
                'calculation_type': calculation_type,
                'filters': filters,
                'result': result
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('تنخواه یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in tankhah calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه تنخواه'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست تنخواه‌ها برای محاسبه بودجه
        
        Returns:
            Response: لیست تنخواه‌ها
        """
        try:
            from tankhah.models import Tankhah
            
            tankhahs = Tankhah.objects.all().values('id', 'number')
            
            return Response({
                'tankhahs': list(tankhahs),
                'total_count': len(tankhahs)
            })
            
        except Exception as e:
            logger.error(f"Error getting tankhahs: {str(e)}")
            return Response({
                'error': _('خطا در دریافت لیست تنخواه‌ها'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
