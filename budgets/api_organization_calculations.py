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
    get_organization_total_budget,
    get_organization_budget,
    get_organization_remaining_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class OrganizationCalculationsAPI(APIView):
    """API برای محاسبات بودجه سازمان"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه سازمان
        
        Parameters:
            organization_id (int): شناسه سازمان
            calculation_type (str): نوع محاسبه (total, budget, remaining, all)
            filters (dict): فیلترهای اضافی
        
        Returns:
            Response: نتیجه محاسبه
        """
        try:
            organization_id = request.data.get('organization_id')
            calculation_type = request.data.get('calculation_type', 'total')
            filters = request.data.get('filters', {})
            
            if not organization_id:
                return Response({
                    'error': _('شناسه سازمان الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from core.models import Organization
            organization = Organization.objects.get(pk=organization_id)
            
            result = {}
            
            if calculation_type == 'total':
                result['total_budget'] = float(get_organization_total_budget(organization, filters))
            elif calculation_type == 'budget':
                result['budget'] = float(get_organization_budget(organization, filters))
            elif calculation_type == 'remaining':
                result['remaining_budget'] = float(get_organization_remaining_budget(organization, filters))
            elif calculation_type == 'all':
                result['total_budget'] = float(get_organization_total_budget(organization, filters))
                result['budget'] = float(get_organization_budget(organization, filters))
                result['remaining_budget'] = float(get_organization_remaining_budget(organization, filters))
            else:
                return Response({
                    'error': _('نوع محاسبه نامعتبر است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # تبدیل به رشته تمیز
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    result[f'{key}_str'] = decimal_to_clean_str(Decimal(str(value)))
            
            return Response({
                'organization_id': organization_id,
                'organization_name': organization.name,
                'calculation_type': calculation_type,
                'filters': filters,
                'result': result
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('سازمان یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in organization calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه سازمان'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست سازمان‌ها برای محاسبه بودجه
        
        Returns:
            Response: لیست سازمان‌ها
        """
        try:
            from core.models import Organization
            
            organizations = Organization.objects.all().values('id', 'name', 'code')
            
            return Response({
                'organizations': list(organizations),
                'total_count': len(organizations)
            })
            
        except Exception as e:
            logger.error(f"Error getting organizations: {str(e)}")
            return Response({
                'error': _('خطا در دریافت لیست سازمان‌ها'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
