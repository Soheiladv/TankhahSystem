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
    get_project_total_budget,
    get_project_used_budget,
    get_project_remaining_budget,
    decimal_to_clean_str
)

logger = logging.getLogger(__name__)

class ProjectCalculationsAPI(APIView):
    """API برای محاسبات بودجه پروژه"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        محاسبه بودجه پروژه
        
        Parameters:
            project_id (int): شناسه پروژه
            calculation_type (str): نوع محاسبه (total, used, remaining, all)
            force_refresh (bool): اجبار به‌روزرسانی کش
            filters (dict): فیلترهای اضافی
        
        Returns:
            Response: نتیجه محاسبه
        """
        try:
            project_id = request.data.get('project_id')
            calculation_type = request.data.get('calculation_type', 'all')
            force_refresh = request.data.get('force_refresh', False)
            filters = request.data.get('filters', {})
            
            if not project_id:
                return Response({
                    'error': _('شناسه پروژه الزامی است')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from core.models import Project
            project = Project.objects.get(pk=project_id)
            
            result = {}
            
            if calculation_type in ['total', 'all']:
                result['total_budget'] = float(get_project_total_budget(project, force_refresh, filters))
            
            if calculation_type in ['used', 'all']:
                result['used_budget'] = float(get_project_used_budget(project, filters))
            
            if calculation_type in ['remaining', 'all']:
                result['remaining_budget'] = float(get_project_remaining_budget(project, force_refresh, filters))
            
            # تبدیل به رشته تمیز
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    result[f'{key}_str'] = decimal_to_clean_str(Decimal(str(value)))
            
            return Response({
                'project_id': project_id,
                'project_name': project.name,
                'calculation_type': calculation_type,
                'force_refresh': force_refresh,
                'filters': filters,
                'result': result
            })
            
        except ObjectDoesNotExist:
            return Response({
                'error': _('پروژه یافت نشد')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in project calculations: {str(e)}")
            return Response({
                'error': _('خطا در محاسبه بودجه پروژه'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        دریافت لیست پروژه‌ها برای محاسبه بودجه
        
        Returns:
            Response: لیست پروژه‌ها
        """
        try:
            from core.models import Project
            
            projects = Project.objects.all().values('id', 'name', 'code')
            
            return Response({
                'projects': list(projects),
                'total_count': len(projects)
            })
            
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            return Response({
                'error': _('خطا در دریافت لیست پروژه‌ها'),
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
